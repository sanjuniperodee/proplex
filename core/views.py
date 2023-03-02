import csv
import json
import os
from email import encoders
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path

import pandas
import pandas as pd
import openpyxl
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
from django.http import JsonResponse
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
            order = get_object_or_404(Order, user=self.request.user, payment=False)
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
            order = get_object_or_404(Order, user=self.request.user, payment=False)
            items = order.items.get_queryset()
            print(items)
            df = pd.DataFrame(columns=['Title', 'Quantity', 'Sum'])
            # pd.concat([df([item.item.title, item.quantity, item.get_final_price()], columns=['Title', 'Quantity', 'Sum']) for item in items],
            #           ignore_index=True)
            for item in items:
                df1 = pd.DataFrame({'Title': [item.item.title], 'Quantity': [item.quantity], 'Sum': [item.get_final_price()]})
                df = df.append(df1, ignore_index=True)
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
                        comments=comment,
                        user=self.request.user,
                    )
                    shipping_address.save()
                    order.shipping_address = shipping_address
                    order.save()
                gmail_user = '87779571856b@gmail.com'
                gmail_app_password = 'iwhbelgfpxbnrmcv'
                sent_from = gmail_user
                sent_to = '87082420482b@gmail.com'
                email_text = "новый заказ"
                message = MIMEMultipart()
                message['From'] = sent_from
                message['To'] = sent_to
                message['Subject'] = 'A test mail sent by Python. It has an attachment.'
                message.attach(MIMEText(email_text, 'plain'))
                df.to_excel("core\\output.xlsx")
                part = MIMEBase('application', "octet-stream")
                with open("core\\output.xlsx", 'rb') as file:
                    part.set_payload(file.read())
                encoders.encode_base64(part)
                part.add_header('Content-Disposition',
                                'attachment; filename={}'.format(Path("core\\output.xlsx").name))
                message.attach(part)
                text = message.as_string()
                try:
                    server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
                    server.ehlo()
                    server.login(gmail_user, gmail_app_password)
                    server.sendmail(sent_from, sent_to, text)
                    server.close()

                    print('Email sent!')
                except Exception as exception:
                    print("Error: %s!\n\n" % exception)
                return redirect("/")
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


@csrf_exempt
def home1(request, ctg, ctg2):
    brandy = []
    if ctg2 == 'all':
        object_list = Item.objects.filter(category__title=ctg).order_by('title')
        brands = SubCategory.objects.filter(category__title=ctg)
    else:
        object_list = Item.objects.filter(category__title=ctg, category__subcategory__title=ctg2).order_by('title')
        brands = Brand.objects.filter(category__title=ctg, category__subcategory__title=ctg2)
    if request.method == "GET":
        print("I'm here mfs")

    if request.method == 'POST':
        if ctg2 == 'all':
            brandy = request.POST.getlist('scales')
            if len(brandy) == 1:
                print('aaaa')
                return redirect("core:home1", ctg=ctg, ctg2=brandy[0])
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
    page_obj = Paginator(Item.objects.get_queryset().filter(category__title='Дверная фурнитура').order_by('title'), 4).get_page(request.GET.get('page'))
    page_obj2 = Paginator(Item.objects.get_queryset().filter(category__title='профиль').order_by('title'), 4).get_page(request.GET.get('page'))
    page_obj3 = Paginator(Item.objects.get_queryset().filter(category__title='москитный профиль').order_by('title'), 4).get_page(request.GET.get('page'))
    page_obj4 = Paginator(Item.objects.get_queryset().filter(category__title='VHS').order_by('title'), 4).get_page(request.GET.get('page'))
    page_obj5 = Paginator(Item.objects.get_queryset().filter(category__title='стеклопакет').order_by('title'), 4).get_page(request.GET.get('page'))
    page_obj6 = Paginator(Item.objects.get_queryset().filter(category__title='Комплектующие').order_by('title'), 4).get_page(request.GET.get('page'))
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


@login_required
def add_to_cart1(request):
    # with open('core/Mika.csv', encoding="utf-16") as f:
    #     reader = csv.reader(f, delimiter='\t')
    #     i = 0
    #     for row in reader:
    #         i+=1
    #         item = Item(title=row[2],
    #                     slug='item' + str(i),
    #                     image='https://media.istockphoto.com/id/92450205/photo/sunsplashed-window.jpg?s=612x612&w=0&k=20&c=dTuhETbiWnoxAR1Ek5ROlj0liKxBazb14d9rsfe4XTc=',
    #                     acrtiul=row[3],
    #                     category=Category.objects.filter(title=row[0], subcategory__title=row[1])[0],
    #                     price=100,
    #                     description="Норма упаковки:" + row[5]
    #                     )
    #         item.save()
    # return JsonResponse({'data': '123'})
    slug = str(request.POST.get('slug'))
    item = get_object_or_404(Item, slug=slug)
    order_item, created = OrderItem.objects.get_or_create(
        item=item,
        user=request.user,
        ordered=False
    )
    order_qs = Order.objects.filter(user=request.user, payment=False)
    if order_qs.exists():
        order = order_qs[0]
        if order.items.filter(item__slug=item.slug).exists():
            order_item.quantity += 1
            order_item.save()
            messages.info(request, "This item quantity was updated.")
        else:
            order.items.add(order_item)
            messages.info(request, "This item was added to your cart.")
    else:
        ordered_date = timezone.now()
        order = Order.objects.create(
            user=request.user, ordered_date=ordered_date)
        order.items.add(order_item)
        messages.info(request, "core:order-summary")
    return JsonResponse({'data': '123'})


def dashboards(request):
    header = {
        'SS-Token': 'b859f200c0ed4ba491f9a4185f6fb64f',
        'Content-Type': 'application/json-patch+json',
        'accept': 'application/json'
    }
    payload = {
        "projectIds": [
            '27316'
        ],
        "includeHidden": True
    }
    result = requests.post('https://api.survey-studio.com/projects/counters', data=json.dumps(payload), headers=header)
    response = result.json()
    context = {
        'ucell_all': response['body'][0]['counters'][1]['value'],
        'beeline_all': response['body'][0]['counters'][30]['value'],
        'mobiuz_all': response['body'][0]['counters'][59]['value'],
        'uzmobile_all': response['body'][0]['counters'][88]['value'],
        'ucell_men': response['body'][0]['counters'][140]['value'],
        'ucell_woman': response['body'][0]['counters'][141]['value'],
        'beeline_men': response['body'][0]['counters'][142]['value'],
        'beeline_woman': response['body'][0]['counters'][143]['value'],
        'mobiuz_men': response['body'][0]['counters'][144]['value'],
        'mobiuz_woman': response['body'][0]['counters'][145]['value'],
        'uzmobile_men': response['body'][0]['counters'][146]['value'],
        'uzmobile_woman': response['body'][0]['counters'][147]['value'],
        'ucell_16_19': response['body'][0]['counters'][154]['value'],
        'ucell_20_24': response['body'][0]['counters'][155]['value'],
        'ucell_25_34': response['body'][0]['counters'][156]['value'],
        'ucell_35_44': response['body'][0]['counters'][157]['value'],
        'ucell_45_54': response['body'][0]['counters'][158]['value'],
        'ucell_55': response['body'][0]['counters'][159]['value'],
        'beeline_16_19': response['body'][0]['counters'][160]['value'],
        'beeline_20_24': response['body'][0]['counters'][161]['value'],
        'beeline_25_34': response['body'][0]['counters'][162]['value'],
        'beeline_35_44': response['body'][0]['counters'][163]['value'],
        'beeline_45_54': response['body'][0]['counters'][164]['value'],
        'beeline_55': response['body'][0]['counters'][165]['value'],
        'mobiuz_16_19': response['body'][0]['counters'][166]['value'],
        'mobiuz_20_24': response['body'][0]['counters'][167]['value'],
        'mobiuz_25_34': response['body'][0]['counters'][168]['value'],
        'mobiuz_35_44': response['body'][0]['counters'][169]['value'],
        'mobiuz_45_54': response['body'][0]['counters'][170]['value'],
        'mobiuz_55': response['body'][0]['counters'][171]['value'],
        'uzmobile_16_19': response['body'][0]['counters'][172]['value'],
        'uzmobile_20_24': response['body'][0]['counters'][173]['value'],
        'uzmobile_25_34': response['body'][0]['counters'][174]['value'],
        'uzmobile_35_44': response['body'][0]['counters'][175]['value'],
        'uzmobile_45_54': response['body'][0]['counters'][175]['value'],
        'uzmobile_55': response['body'][0]['counters'][177]['value'],
        'ucell_center': response['body'][0]['counters'][182]['value'],
        'ucell_city': response['body'][0]['counters'][183]['value'],
        'ucell_pgt': response['body'][0]['counters'][184]['value'],
        'ucell_village': response['body'][0]['counters'][185]['value'],
        'beeline_center': response['body'][0]['counters'][186]['value'],
        'beeline_city': response['body'][0]['counters'][187]['value'],
        'beeline_pgt': response['body'][0]['counters'][188]['value'],
        'beeline_village': response['body'][0]['counters'][189]['value'],
        'mobiuz_center': response['body'][0]['counters'][190]['value'],
        'mobiuz_city': response['body'][0]['counters'][191]['value'],
        'mobiuz_pgt': response['body'][0]['counters'][192]['value'],
        'mobiuz_village': response['body'][0]['counters'][193]['value'],
        'uzmobile_center': response['body'][0]['counters'][194]['value'],
        'uzmobile_city': response['body'][0]['counters'][195]['value'],
        'uzmobile_pgt': response['body'][0]['counters'][196]['value'],
        'uzmobile_village': response['body'][0]['counters'][197]['value'],
        'ucell_work': response['body'][0]['counters'][198]['value'],
        'beeline_work': response['body'][0]['counters'][199]['value'],
        'mobiuz_work': response['body'][0]['counters'][200]['value'],
        'uzmobile_work': response['body'][0]['counters'][201]['value'],
        'ucell_conversations': response['body'][0]['counters'][202]['value'],
        'beeline_conversations': response['body'][0]['counters'][203]['value'],
        'mobiuz_conversations': response['body'][0]['counters'][204]['value'],
        'uzmobile_conversations': response['body'][0]['counters'][205]['value'],
        'ucell_calls': response['body'][0]['counters'][206]['value'],
        'beeline_calls': response['body'][0]['counters'][207]['value'],
        'mobiuz_calls': response['body'][0]['counters'][208]['value'],
        'uzmobile_calls': response['body'][0]['counters'][209]['value'],
        'ucell_internet': response['body'][0]['counters'][210]['value'],
        'beeline_internet': response['body'][0]['counters'][211]['value'],
        'mobiuz_internet': response['body'][0]['counters'][212]['value'],
        'uzmobile_internet': response['body'][0]['counters'][213]['value'],
        'ucell1sim': response['body'][0]['counters'][214]['value'],
        'ucell2sim': response['body'][0]['counters'][215]['value'],
        'beeline1sim': response['body'][0]['counters'][216]['value'],
        'beeline2sim': response['body'][0]['counters'][217]['value'],
        'mobiuz1sim': response['body'][0]['counters'][218]['value'],
        'mobiuz2sim': response['body'][0]['counters'][219]['value'],
        'uzmobile1sim': response['body'][0]['counters'][220]['value'],
        'uzmobile2sim': response['body'][0]['counters'][221]['value'],
        'ucelld3': response['body'][0]['counters'][222]['value'],
        'ucelld6': response['body'][0]['counters'][223]['value'],
        'ucelld12': response['body'][0]['counters'][224]['value'],
        'ucelld36': response['body'][0]['counters'][225]['value'],
        'ucelld60': response['body'][0]['counters'][226]['value'],
        'ucelld120': response['body'][0]['counters'][227]['value'],
        'beelined3': response['body'][0]['counters'][228]['value'],
        'beelined6': response['body'][0]['counters'][229]['value'],
        'beelined12': response['body'][0]['counters'][230]['value'],
        'beelined36': response['body'][0]['counters'][231]['value'],
        'beelined60': response['body'][0]['counters'][232]['value'],
        'beelined120': response['body'][0]['counters'][233]['value'],
        'mobiuzd3': response['body'][0]['counters'][234]['value'],
        'mobiuzd6': response['body'][0]['counters'][235]['value'],
        'mobiuzd12': response['body'][0]['counters'][236]['value'],
        'mobiuzd36': response['body'][0]['counters'][237]['value'],
        'mobiuzd60': response['body'][0]['counters'][238]['value'],
        'mobiuzd120': response['body'][0]['counters'][239]['value'],
        'uzmobiled3': response['body'][0]['counters'][240]['value'],
        'uzmobiled6': response['body'][0]['counters'][241]['value'],
        'uzmobiled12': response['body'][0]['counters'][242]['value'],
        'uzmobiled36': response['body'][0]['counters'][243]['value'],
        'uzmobiled60': response['body'][0]['counters'][244]['value'],
        'uzmobiled120': response['body'][0]['counters'][245]['value'],
        'ucell_main': response['body'][0]['counters'][246]['value'],
        'ucell_second': response['body'][0]['counters'][247]['value'],
        'mobiuz_main': response['body'][0]['counters'][248]['value'],
        'mobiuz_second': response['body'][0]['counters'][249]['value'],
        'uzmobile_main': response['body'][0]['counters'][250]['value'],
        'uzmobile_second': response['body'][0]['counters'][251]['value'],
        'ucell_ucell': response['body'][0]['counters'][252]['value'],
        'ucell_beeline': response['body'][0]['counters'][253]['value'],
        'ucell_mobiuz': response['body'][0]['counters'][254]['value'],
        'ucell_uzmobile': response['body'][0]['counters'][255]['value'],
        'beeline_ucell': response['body'][0]['counters'][256]['value'],
        'beeline_beeline': response['body'][0]['counters'][257]['value'],
        'beeline_mobiuz': response['body'][0]['counters'][258]['value'],
        'beeline_uzmobile': response['body'][0]['counters'][259]['value'],
        'mobiuz_ucell': response['body'][0]['counters'][260]['value'],
        'mobiuz_beeline': response['body'][0]['counters'][261]['value'],
        'mobiuz_mobiuz': response['body'][0]['counters'][262]['value'],
        'mobiuz_uzmobile': response['body'][0]['counters'][263]['value'],
        'uzmobile_ucell': response['body'][0]['counters'][264]['value'],
        'uzmobile_beeline': response['body'][0]['counters'][265]['value'],
        'uzmobile_mobiuz': response['body'][0]['counters'][266]['value'],
        'uzmobile_uzmobile': response['body'][0]['counters'][267]['value'],
        'beeline_p': response['body'][0]['counters'][118]['value'],
        'beeline_n': response['body'][0]['counters'][119]['value'],
        'beeline_nps': (int)((response['body'][0]['counters'][118]['value'] - response['body'][0]['counters'][120]['value']) /
                             (response['body'][0]['counters'][120]['value'] + response['body'][0]['counters'][119]['value'] + response['body'][0]['counters'][118]['value'])
                             * 100),
        'beeline_k': response['body'][0]['counters'][120]['value'],
        'mobiuz_p': response['body'][0]['counters'][121]['value'],
        'mobiuz_n': response['body'][0]['counters'][122]['value'],
        'mobiuz_nps': (int)(
            (response['body'][0]['counters'][121]['value'] - response['body'][0]['counters'][123]['value']) / (
                        response['body'][0]['counters'][121]['value'] + response['body'][0]['counters'][122]['value'] +
                        response['body'][0]['counters'][123]['value']) * 100),
        'mobiuz_k': response['body'][0]['counters'][123]['value'],
        'ucell_p': response['body'][0]['counters'][124]['value'],
        'ucell_n': response['body'][0]['counters'][125]['value'],
        'ucell_nps': (int)(
            (response['body'][0]['counters'][124]['value'] - response['body'][0]['counters'][126]['value']) / (
                        response['body'][0]['counters'][124]['value'] + response['body'][0]['counters'][125]['value'] +
                        response['body'][0]['counters'][126]['value']) * 100),
        'ucell_k': response['body'][0]['counters'][126]['value'],
        'uzmobile_p': response['body'][0]['counters'][127]['value'],
        'uzmobile_n': response['body'][0]['counters'][128]['value'],
        'uzmobile_nps': (int)(
            (response['body'][0]['counters'][127]['value'] - response['body'][0]['counters'][129]['value']) / (
                        response['body'][0]['counters'][127]['value'] + response['body'][0]['counters'][128]['value'] +
                        response['body'][0]['counters'][129]['value']) * 100),
        'uzmobile_k': response['body'][0]['counters'][129]['value'],
    }
    # print(response['body'][0]['counters'][124]['value'])
    # print(context)
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
        messages.info(request, "core:order-summary")
        return redirect("/")


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
        if order.items.filter(item__slug=item.slug).exists():
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