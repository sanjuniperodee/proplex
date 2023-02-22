import os
import random
import string
import smtplib
import urllib.request
import subprocess
import stripe
import requests
from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.core.exceptions import ObjectDoesNotExist
from django.core.paginator import Paginator
from django.shortcuts import redirect
from django.shortcuts import render, get_object_or_404
from django.utils import timezone
from django.views.generic import ListView, DetailView, View
from django.views.decorators.csrf import csrf_exempt

from .forms import CheckoutForm, CouponForm, RefundForm, PaymentForm
from .models import Item, OrderItem, Order, Address, Coupon, Refund, UserProfile, Brand, Category, SubCategory


stripe.api_key = settings.STRIPE_SECRET_KEY


def create_ref_code():
    return ''.join(random.choices(string.ascii_lowercase + string.digits, k=20))


def products(request):
    context = {
        'items': Item.objects.all()
    }
    return render(request, "products.html", context)


def is_valid_form(values):
    valid = True
    for field in values:
        if field == '':
            valid = False
    return valid


class CheckoutView(View):
    def get(self, *args, **kwargs):
        try:
            order = Order.objects.get(user=self.request.user, payment=False)
            form = CheckoutForm()
            context = {
                'form': form,
                'couponform': CouponForm(),
                'order': order,
                'DISPLAY_COUPON_FORM': True
            }
            return render(self.request, "checkout.html", context)
        except ObjectDoesNotExist:
            messages.info(self.request, "You do not have an active order")
            return redirect("core:checkout")

    def post(self, *args, **kwargs):
        form = CheckoutForm(self.request.POST or None)
        try:
            order = Order.objects.get(user=self.request.user, payment=False)
            if form.is_valid():
                print("User is entering a new shipping address")
                shipping_address = form.cleaned_data.get(
                    'shipping_address')
                phone_number = form.cleaned_data.get(
                    'phone_number')
                comment = form.cleaned_data.get(
                    'comment')
                if is_valid_form([shipping_address, comment, phone_number]):
                    shipping_address = Address(
                        phone_number=phone_number,
                        comment=comment,
                        user=self.request.user,
                        address_type='S'
                    )
                    shipping_address.save()
                    order.shipping_address = shipping_address
                    order.save()
                gmail_user = '87779571856b@gmail.com'
                gmail_app_password = 'mpxmpwvfpxonbbjv'
                sent_from = gmail_user
                sent_to = ['87082420482b@gmail.com']
                sent_subject = "Hey Friends!"
                sent_body = ("Hey, what's up? friend!\n\n"
                             "I hope you have been well!\n"
                             "\n"
                             "Cheers,\n"
                             "Jay\n")

                email_text = """\
                From: %s
                To: %s
                Subject: %s

                %s
                """ % (sent_from, ", ".join(sent_to), sent_subject, sent_body)
                text = order.items
                try:
                    server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
                    server.ehlo()
                    server.login(gmail_user, gmail_app_password)
                    server.sendmail(sent_from, sent_to, email_text)
                    server.close()

                    print('Email sent!')
                except Exception as exception:
                    print("Error: %s!\n\n" % exception)
                return  redirect("/")
        except ObjectDoesNotExist:
            messages.warning(self.request, "You do not have an active order")
            return redirect("core:order-summary")

def SuccesPayment(request):
    order = Order.objects.get(id=request.GET.get('pg_order_id'))
    order_items = order.items.all()
    order_items.update(payment=True)
    for item in order_items:
        item.save()
    order.ordered_date = timezone.now()
    order.payment = True
    order.ref_code = create_ref_code()
    order.save()
    messages.success(request, "Your order was successful!")
    return redirect("/")

class HomeView(ListView):
    model = Item
    paginate_by = 10
    template_name = "home.html"


@csrf_exempt
def home1(request, ctg, ctg2):
    brandy = []
    if ctg2 == 'all':
        object_list = Item.objects.filter(category__title=ctg).order_by('title')
        brands = SubCategory.objects.filter(category__title=ctg)
    else:
        object_list = Item.objects.filter(category__title=ctg, category__subcategory__title=ctg2).order_by('title')
        brands = Brand.objects.filter(category__title=ctg, category__subcategory__title=ctg2)
    if request.method == 'POST':
        if ctg2 == 'all':
            brandy = request.POST.getlist('scales')
            if len(brandy) == 1:
                print('aaaa')
                return redirect("http://www.ybeauty.kz/filter/" + ctg + "/" + brandy[0])
            object_list = []
            i = 0
            for brand in brandy:
                i+=1
                object_list += Item.objects.filter(category__title=ctg, category__subcategory__title=brand).order_by('title')
            if i == 0:
                object_list = Item.objects.filter(category__title=ctg)
        else:
            brandy = request.POST.getlist('scales')
            object_list = []
            i = 0
            for brand in brandy:
                i+=1
                object_list += Item.objects.filter(category__title=ctg, category__subcategory__title=ctg2, brand__title=brand).order_by('title')
            if i == 0:
                object_list = Item.objects.filter(category__title=ctg, category__subcategory__title=ctg2).order_by('title')
    paginator = Paginator(object_list, 12)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'brandy': brandy,
        'str1': ctg2,
        'str': ctg,
        'object_list': page_obj,
        'brands': brands,
    }
    return render(request, 'shopping_page.html', context)


@csrf_exempt
def home(request):
    page_obj = Paginator(Item.objects.get_queryset().filter(category__title='Парфюмы').order_by('title'), 4).get_page(request.GET.get('page'))
    page_obj2 = Paginator(Item.objects.get_queryset().filter(category__title='Уход за Кожей').order_by('title'), 4).get_page(request.GET.get('page'))
    page_obj3 = Paginator(Item.objects.get_queryset().filter(category__title='Уход за Волосами').order_by('title'), 4).get_page(request.GET.get('page'))
    page_obj4 = Paginator(Item.objects.get_queryset().filter(category__title='Декоративная Косметика').order_by('title'), 4).get_page(request.GET.get('page'))
    page_obj5 = Paginator(Item.objects.get_queryset().filter(category__title='Подарочный Набор').order_by('title'), 4).get_page(request.GET.get('page'))
    page_obj6 = Paginator(Item.objects.get_queryset().filter(category__title='Для Дома').order_by('title'), 4).get_page(request.GET.get('page'))
    context = {
        'str': 'none',
        'object_list': page_obj,
        'object_list2': page_obj2,
        'object_list3': page_obj3,
        'object_list4': page_obj4,
        'object_list5': page_obj5,
        'object_list6': page_obj6

    }
    return render(request, 'home_page.html', context)


def carousel(request):
    return render(request, 'carousel.html')

def dashboards(request):
    headers = {
        'SS-Token': 'b859f200c0ed4ba491f9a4185f6fb64f'
    }
    result = requests.get('https://api.survey-studio.com/projects/17169/counters', headers=headers)
    # print(result)
    response = result.json()
    context = {
        'men': response['body'][9]['quota'],
        'woman': response['body'][10]['quota']

    }
    print(response)
    return render(request, 'dashboards.html', context)



@login_required
def order_summary(request):
    try:
        order = Order.objects.get_queryset().filter(user=request.user, payment=False)
        context = {
            'objects': order
        }
        return render(request, 'order_summary.html', context)
    except ObjectDoesNotExist:
        messages.warning(request, "You do not have an active order")
        return redirect("/")


class ItemDetailView(DetailView):
    model = Item
    template_name = "detail.html"


@login_required
def add_to_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_item, created = OrderItem.objects.get_or_create(
        item=item,
        user=request.user,
        ordered=False

    )
    order_qs = Order.objects.filter(user=request.user, payment=False)
    if order_qs.exists():
        order = order_qs[0]
        # check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item.quantity += 1
            order_item.save()
            messages.info(request, "This item quantity was updated.")
            return redirect("core:order-summary")
        else:
            order.items.add(order_item)
            messages.info(request, "This item was added to your cart.")
            return redirect("core:order-summary")
    else:
        ordered_date = timezone.now()
        order = Order.objects.create(
            user=request.user, ordered_date=ordered_date)
        order.items.add(order_item)
        messages.info(request, "This item was added to your cart.")
        return redirect("core:order-summary")


@login_required
def remove_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(
        user=request.user,
        payment=False,
    )
    if order_qs.exists():
        order = order_qs[0]
        # check if the order item is in the order
        if order.items.fiaddlter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                user=request.user,
                ordered=False
            )[0]
            order.items.remove(order_item)
            order_item.delete()
            messages.info(request, "This item was removed from your cart.")
            return redirect("core:order-summary")
        else:
            messages.info(request, "This item was not in your cart")
            return redirect("core:product", slug=slug)
    else:
        messages.info(request, "You do not have an active order")
        return redirect("core:product", slug=slug)


@login_required
def remove_single_item_from_cart(request, slug):
    item = get_object_or_404(Item, slug=slug)
    order_qs = Order.objects.filter(
        user=request.user,
        payment=False
    )
    if order_qs.exists():
        order = order_qs[0]
        # check if the order item is in the order
        if order.items.filter(item__slug=item.slug).exists():
            order_item = OrderItem.objects.filter(
                item=item,
                user=request.user,
                ordered=False
            )[0]
            if order_item.quantity > 1:
                order_item.quantity -= 1
                order_item.save()
            else:
                order.items.remove(order_item)
            messages.info(request, "This item quantity was updated.")
            return redirect("core:order-summary")
        else:
            messages.info(request, "This item was not in your cart")
            return redirect("core:product", slug=slug)
    else:
        messages.info(request, "You do not have an active order")
        return redirect("core:product", slug=slug)


def get_coupon(request, code):
    try:
        coupon = Coupon.objects.get(code=code)
        return coupon
    except ObjectDoesNotExist:
        messages.info(request, "This coupon does not exist")
        return redirect("core:checkout")


class AddCouponView(View):
    def post(self, *args, **kwargs):
        form = CouponForm(self.request.POST or None)
        if form.is_valid():
            try:
                code = form.cleaned_data.get('code')
                order = Order.objects.get(
                    user=self.request.user, ordered=False)
                order.coupon = get_coupon(self.request, code)
                order.save()
                messages.success(self.request, "Successfully added coupon")
                return redirect("core:checkout")
            except ObjectDoesNotExist:
                messages.info(self.request, "You do not have an active order")
                return redirect("core:checkout")


class RequestRefundView(View):
    def get(self, *args, **kwargs):
        form = RefundForm()
        context = {
            'form': form
        }
        return render(self.request, "request_refund.html", context)

    def post(self, *args, **kwargs):
        form = RefundForm(self.request.POST)
        if form.is_valid():
            ref_code = form.cleaned_data.get('ref_code')
            message = form.cleaned_data.get('message')
            email = form.cleaned_data.get('email')
            # edit the order
            try:
                order = Order.objects.get(ref_code=ref_code)
                order.refund_requested = True
                order.save()

                # store the refund
                refund = Refund()
                refund.order = order
                refund.reason = message
                refund.email = email
                refund.save()

                messages.info(self.request, "Your request was received.")
                return redirect("core:request-refund")

            except ObjectDoesNotExist:
                messages.info(self.request, "This order does not exist.")
                return redirect("core:request-refund")
# data = {
#                     'pg_order_id': order.id,
#                     'pg_merchant_id': "545774",
#                     'pg_amount': int(order.get_total()),
#                     'pg_description': "test",
#                     'pg_salt': "ybeauty",
#                     'pg_sig': content,
#                     'pg_success_url': 'http://ybeauty.kz:81/successPayment/',
#                     'pg_failure_url': 'http://ybeauty.kz:81/checkout/',
#                     'pg_success_url_method': 'GET',
#                     'pg_failure_url_method': 'GET',
#                 }