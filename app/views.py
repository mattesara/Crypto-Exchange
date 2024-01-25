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


def trade_view(request):                                                    #trade_view with OrderForm allows users to enter their orders to make trades
    profile = Profile.objects.get(user=request.user)
    balance = profile.balance
    if request.method == "POST":
        form = OrderForm(request.POST)
        if form.is_valid():                                                 #check if entered form is valid
            profile = get_object_or_404(Profile, user=request.user)         #obtaining profile instance
            order = form.save(commit=False)
            order.profile = profile
            order.datetime = timezone.now()
            if order.SELL:                                                  #if order type is sell, it checks that user has the cryptocurrencies he wants to sell
                if order.quantity <= profile.balance:                       
                    order.order_id = ObjectId()                             #obtaining order_id for run the function to execute order
                    order_id = order.order_id
                    order.save()
                    execute_sell_order(order_id)                            #then the order filling function is performed
                else:
                    message = ('Non hai abbastanza fondi per completare questa transazione')            #otherwise, the user is warned that he does not have enough funds
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
    order = get_object_or_404(Order, order_id=order_id)                                #get order object by order_id
    while not order.executed:                                                          #cycle that carries out the function until the main order is completely filled
        matching_order = Order.objects.filter(type_order='SELL', price__lte=order.price, executed=False).order_by(
                'price',                                                               
                'datetime').first()                                                    #search for matching_order that can satisfy at least a part of the order
        if matching_order:
            Transaction.objects.create(buyer=order.profile, seller=matching_order.profile, buy_order=order,                #if there, create transaction with users data
                                           sell_order=matching_order, price=matching_order.price, datetime=timezone.now,
                                           quantity=min(order.remaining_quantity, matching_order.remaining_quantity))
            order.profile.balance += Transaction.quantity                              #updating users' crypto balance
            matching_order.profile.balance -= Transaction.quantity
            total_order = Transaction.price * Transaction.quantity                     #updating users' dollar balance
            order.profile.dollar_balance -= total_order
            matching_order.profile.dollar_balance += total_order
            if order.remaining_quantity == matching_order.remaining_quantity:          #comparison order remaining quantities to see if both orders has been completely filled or not
                order.executed = True
                matching_order.executed = True
                order.save()
                matching_order.save()                                                  #if so, the orders are both executed
                return HttpResponse('Order completed!')
            if order.remaining_quantity > matching_order.remaining_quantity:           #otherwise, only the completed filled order are executed
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


def orders_view(request):                                                                #view to show the entire list of active orders
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


def profit_view(request):                                                                #functionality to show the profit of profile
    response = []
    profile = Profile.objects.get(user=request.user)
    buy_orders = Order.objects.filter(profile=profile, type_order='BUY', executed=True)                #search for user' executed orders
    sell_orders = Order.objects.filter(profile=profile, type_order='SELL', executed=True)
    result_buy_orders = []
    result_sell_orders = []
    for buy_order in buy_orders:
        tot_buy_order = buy_order.price * buy_order.quantity                              #calculation of the total value of each user's order
        result_buy_orders.append(tot_buy_order)
    for sell_order in sell_orders:
        tot_sell_order = sell_order.price * sell_order.quantity
        result_sell_orders.append(tot_sell_order)
    total_buy_orders = sum(result_buy_orders)                                            #calculation of the total of all purchase and all sale orders placed by the user
    total_sell_orders = sum(result_sell_orders)
    if total_buy_orders > total_sell_orders:
        loss = total_buy_orders - total_sell_orders                                     #by subtracting the two totals I check whether the user had a profit or a loss
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
