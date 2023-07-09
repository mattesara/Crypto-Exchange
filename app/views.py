from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.forms import AuthenticationForm, UserCreationForm
from django.contrib.auth import login, logout
from .models import *
from .forms import OrderForm
from django.utils import timezone
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from bson.objectid import ObjectId
from django.db.models import Sum


def register(request):
    if request.method == 'POST':
        form = UserCreationForm(request.POST)
        if form.is_valid():
            form.save()
            return render(request, 'app/homepage.html')
    else:
        form = UserCreationForm()
    return render(request, 'app/register.html', {'form': form})


def login_view(request):
    if request.method == 'POST':
        form = AuthenticationForm(data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            return redirect('trade_view')
    else:
        form = AuthenticationForm()
    return render(request, 'app/login_view.html', {'form': form})


def logout_view(request):
    logout(request)
    return redirect('login_view')


def homepage(request):
    return render(request, 'app/homepage.html')


def trade_view(request):
    profile = Profile.objects.get(user=request.user)
    balance = profile.balance
    if request.method == "POST":
        form = OrderForm(request.POST)
        if form.is_valid():
            profile = get_object_or_404(Profile, user=request.user)
            order = form.save(commit=False)
            order.profile = profile
            order.datetime = timezone.now()
            if order.SELL:
                if order.quantity <= profile.balance:
                    order.order_id = ObjectId()
                    order_id = order.order_id
                    order.save()
                    execute_sell_order(order_id)
                else:
                    message = ('Non hai abbastanza fondi per completare questa transazione')
                    form = OrderForm()
                    return render(request, 'app/trade_view.html',
                                  {'form': form, 'balance': balance, 'message': message})
            else:
                order.order_id = ObjectId()
                order_id = order.order_id
                order.save()
                execute_buy_order(order_id)
    else:
        form = OrderForm()
        return render(request, 'app/trade_view.html', {'form': form, 'balance': balance})


def execute_buy_order(order_id):
    order = get_object_or_404(Order, order_id=order_id)
    while not order.executed:
        matching_order = Order.objects.filter(type_order='SELL', price__lte=order.price, executed=False).order_by(
                'price',
                'datetime').first()
        if matching_order:
            Transaction.objects.create(buyer=order.profile, seller=matching_order.profile, buy_order=order,
                                           sell_order=matching_order, price=matching_order.price, datetime=timezone.now,
                                           quantity=min(order.remaining_quantity, matching_order.remaining_quantity))
            order.profile.balance += Transaction.quantity
            matching_order.profile.balance -= Transaction.quantity
            total_order = Transaction.price * Transaction.quantity
            order.profile.dollar_balance -= total_order
            matching_order.profile.dollar_balance += total_order
            if order.remaining_quantity == matching_order.remaining_quantity:
                order.executed = True
                matching_order.executed = True
                order.save()
                matching_order.save()
                return HttpResponse('Order completed!')
            if order.remaining_quantity > matching_order.remaining_quantity:
                order.remaining_quantity -= Transaction.quantity
                matching_order.executed = True
                order.save()
                matching_order.save()
                return HttpResponse('Order was partially filled!')
            if order.remaining_quantity < matching_order.remaining_quantity:
                matching_order.remaining_quantity -= Transaction.quantity
                order.executed = True
                order.save()
                matching_order.save()
                return HttpResponse('Order completed!')
        else:
            return redirect('homepage')


def execute_sell_order(order_id):
    order = get_object_or_404(Order, order_id=order_id)
    while not order.executed:
        matching_order = Order.objects.filter(type_order='BUY', price__gte=order.price, executed=False).order_by('-price',
                                                                                                             'datetime').first()
        if matching_order:
            Transaction.objects.create(buyer=matching_order.profile, seller=order.profile, buy_order=matching_order,
                                   sell_order=order, price=order.price, datetime=timezone.now,
                                   quantity=min(order.remaining_quantity, matching_order.remaining_quantity))
            order.profile.balance -= Transaction.quantity
            matching_order.profile.balance += Transaction.quantity
            total_order = Transaction.price * Transaction.quantity
            order.profile.dollar_balance += total_order
            matching_order.profile.dollar_balance -= total_order
            if order.remaining_quantity == matching_order.remaining_quantity:
                matching_order.executed = True
                order.executed = True
                order.save()
                matching_order.save()
                return HttpResponse('Order completed!')
            if order.remaining_quantity > matching_order.remaining_quantity:
                order.remaining_quantity -= Transaction.quantity
                matching_order.executed = True
                order.save()
                matching_order.save()
                return HttpResponse('Order was partially filled!')
            if order.remaining_quantity < matching_order.remaining_quantity:
                matching_order.remaining_quantity -= Transaction.quantity
                order.executed = True
                order.save()
                matching_order.save()
                return HttpResponse('Order completed!')

        else:
            return redirect('homepage')


def orders_view(request):
    response = []
    active_orders = Order.objects.filter(executed=False).order_by('-datetime')
    for active_order in active_orders:
        response.append(
            {
                'order_id': active_order.order_id,
                'profile': active_order.profile,
                'datetime': active_order.datetime,
                'price': active_order.price,
                'quantity': active_order.quantity,
                'remaining_quantity': active_order.remaining_quantity,
                'type_order': active_order.type_order

            }
        )
    return JsonResponse(response)


def profit_view(request):
    response = []
    profile = Profile.objects.get(user=request.user)
    buy_orders = Order.objects.filter(profile=profile, type_order='BUY', executed=True)
    sell_orders = Order.objects.filter(profile=profile, type_order='SELL', executed=True)
    total_buy_price = buy_orders.aggregate(Sum('price'))
    total_sell_price = sell_orders.aggregate(Sum('price'))
    total_buy_quantity = buy_orders.aggregate(Sum('quantity'))
    total_sell_quantity = sell_orders.aggregate(Sum('quantity'))
    total_buy_orders = total_buy_price * total_buy_quantity
    total_sell_orders = total_sell_price * total_sell_quantity
    if total_buy_orders > total_sell_orders:
        loss = total_buy_orders - total_sell_orders
        response.append(
            {
                'loss': loss
            }
        )
        return JsonResponse(response)
    else:
        profit = total_sell_orders - total_buy_orders
        response.append(
            {
                'profit': profit
            }
        )
        return JsonResponse(response)
