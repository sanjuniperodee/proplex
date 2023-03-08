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
# import urllib.requestx
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
    elif ctg2 == 'price_up':
        object_list = Item.objects.filter(category__title=ctg).order_by('price')
        brands = SubCategory.objects.filter(category__title=ctg)
    elif ctg2 == 'price_down':
        object_list = Item.objects.filter(category__title=ctg).order_by('-price')
        brands = SubCategory.objects.filter(category__title=ctg)
    else:
        object_list = Item.objects.filter(category__title=ctg, category__subcategory__title=ctg2).order_by('title')
        brands = Brand.objects.filter(category__title=ctg, category__subcategory__title=ctg2)
    if request.method == "GET":
        print("I'm here mfs")

    if request.method == 'POST':
        brandy = request.POST.getlist('scales')
        object_list = []
        i = 0
        for brand in brandy:
            i+=1
            object_list += Item.objects.filter(category__title=ctg, category__subcategory__title=brand).order_by('title')
        if i == 0:
            object_list = Item.objects.filter(category__title=ctg)
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

    page_obj = Paginator(Item.objects.get_queryset().filter(category__title='Дверная фурнитура').order_by('title'), 6).get_page(request.GET.get('page'))
    item1 = page_obj[0]
    page_obj2 = Paginator(Item.objects.get_queryset().filter(category__title='профиль').order_by('title'), 6).get_page(request.GET.get('page'))
    page_obj3 = Paginator(Item.objects.get_queryset().filter(category__title='москитный профиль').order_by('title'), 6).get_page(request.GET.get('page'))
    page_obj4 = Paginator(Item.objects.get_queryset().filter(category__title='VHS').order_by('title'), 6).get_page(request.GET.get('page'))
    page_obj5 = Paginator(Item.objects.get_queryset().filter(category__title='стеклопакет').order_by('title'), 6).get_page(request.GET.get('page'))
    page_obj6 = Paginator(Item.objects.get_queryset().filter(category__title='Комплектующие').order_by('title'), 6).get_page(request.GET.get('page'))
    context = {
        'str': 'none',
        'item1' : item1,
        'object_list': page_obj[1:],
        'object_list2': page_obj2,
        'object_list3': page_obj3,
        'object_list4': page_obj4,
        'object_list5': page_obj5,
        'object_list6': page_obj6
    }

    return render(request, 'index.html', context)


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
    mens = [response['body'][0]['counters'][140]['value'],response['body'][0]['counters'][142]['value'],response['body'][0]['counters'][144]['value'],response['body'][0]['counters'][146]['value']]
    womans = [response['body'][0]['counters'][141]['value'],response['body'][0]['counters'][143]['value'],response['body'][0]['counters'][145]['value'],response['body'][0]['counters'][147]['value']]
    y16_19 = [response['body'][0]['counters'][154]['value'],response['body'][0]['counters'][160]['value'],response['body'][0]['counters'][166]['value'],response['body'][0]['counters'][172]['value']]
    y20_24 = [response['body'][0]['counters'][155]['value'],response['body'][0]['counters'][161]['value'],response['body'][0]['counters'][167]['value'],response['body'][0]['counters'][173]['value']]
    y25_34 = [response['body'][0]['counters'][156]['value'],response['body'][0]['counters'][162]['value'],response['body'][0]['counters'][168]['value'],response['body'][0]['counters'][174]['value']]
    y35_44 = [response['body'][0]['counters'][157]['value'],response['body'][0]['counters'][163]['value'],response['body'][0]['counters'][169]['value'],response['body'][0]['counters'][175]['value']]
    y45_54 = [response['body'][0]['counters'][158]['value'],response['body'][0]['counters'][164]['value'],response['body'][0]['counters'][170]['value'],response['body'][0]['counters'][176]['value']]
    y55 = [response['body'][0]['counters'][159]['value'],response['body'][0]['counters'][165]['value'],response['body'][0]['counters'][171]['value'],response['body'][0]['counters'][177]['value']]
    center = [response['body'][0]['counters'][182]['value'],response['body'][0]['counters'][186]['value'],response['body'][0]['counters'][194]['value'],response['body'][0]['counters'][190]['value']]
    city = [response['body'][0]['counters'][183]['value'],response['body'][0]['counters'][187]['value'],response['body'][0]['counters'][195]['value'],response['body'][0]['counters'][191]['value']]
    pgt = [response['body'][0]['counters'][184]['value'],response['body'][0]['counters'][188]['value'],response['body'][0]['counters'][196]['value'],response['body'][0]['counters'][192]['value']]
    village = [response['body'][0]['counters'][185]['value'],response['body'][0]['counters'][189]['value'],response['body'][0]['counters'][197]['value'],response['body'][0]['counters'][193]['value']]
    work = [response['body'][0]['counters'][198]['value'],response['body'][0]['counters'][199]['value'],response['body'][0]['counters'][201]['value'],response['body'][0]['counters'][200]['value']]
    conversations = [response['body'][0]['counters'][202]['value'],response['body'][0]['counters'][203]['value'],response['body'][0]['counters'][205]['value'],response['body'][0]['counters'][204]['value']]
    calls = [response['body'][0]['counters'][206]['value'],response['body'][0]['counters'][207]['value'],response['body'][0]['counters'][209]['value'],response['body'][0]['counters'][208]['value']]
    internet = [response['body'][0]['counters'][210]['value'],response['body'][0]['counters'][211]['value'],response['body'][0]['counters'][213]['value'],response['body'][0]['counters'][212]['value'],]
    sim1 = [response['body'][0]['counters'][214]['value'],response['body'][0]['counters'][216]['value'],response['body'][0]['counters'][220]['value'],response['body'][0]['counters'][218]['value']]
    sim2 = [response['body'][0]['counters'][215]['value'],response['body'][0]['counters'][217]['value'],response['body'][0]['counters'][221]['value'],response['body'][0]['counters'][219]['value'],]
    month3 = [response['body'][0]['counters'][222]['value'],response['body'][0]['counters'][228]['value'],response['body'][0]['counters'][240]['value'],response['body'][0]['counters'][234]['value']]
    month6 = [response['body'][0]['counters'][223]['value'],response['body'][0]['counters'][229]['value'],response['body'][0]['counters'][241]['value'],response['body'][0]['counters'][235]['value']]
    month12 = [response['body'][0]['counters'][224]['value'],response['body'][0]['counters'][230]['value'],response['body'][0]['counters'][242]['value'],response['body'][0]['counters'][236]['value']]
    month36 = [response['body'][0]['counters'][225]['value'],response['body'][0]['counters'][231]['value'],response['body'][0]['counters'][243]['value'],response['body'][0]['counters'][237]['value']]
    month60 = [response['body'][0]['counters'][226]['value'],response['body'][0]['counters'][232]['value'],response['body'][0]['counters'][244]['value'],response['body'][0]['counters'][238]['value']]
    month120 = [response['body'][0]['counters'][227]['value'],response['body'][0]['counters'][233]['value'],response['body'][0]['counters'][245]['value'],response['body'][0]['counters'][239]['value']]
    main = [response['body'][0]['counters'][246]['value'],response['body'][0]['counters'][248]['value'],response['body'][0]['counters'][250]['value'],response['body'][0]['counters'][250]['value']]
    second = [response['body'][0]['counters'][247]['value'],response['body'][0]['counters'][249]['value'],response['body'][0]['counters'][251]['value'],response['body'][0]['counters'][253]['value']]
    ucell_dop = [response['body'][0]['counters'][254]['value'],response['body'][0]['counters'][255]['value'],response['body'][0]['counters'][257]['value'],response['body'][0]['counters'][256]['value']]
    beeline_dop = [response['body'][0]['counters'][258]['value'],response['body'][0]['counters'][259]['value'],response['body'][0]['counters'][261]['value'],response['body'][0]['counters'][260]['value']]
    uzmobile_dop = [response['body'][0]['counters'][266]['value'],response['body'][0]['counters'][267]['value'],response['body'][0]['counters'][268]['value'],response['body'][0]['counters'][269]['value']]
    mobiuz_dop = [response['body'][0]['counters'][262]['value'],response['body'][0]['counters'][263]['value'],response['body'][0]['counters'][264]['value'],response['body'][0]['counters'][265]['value']]
    beeline = [response['body'][0]['counters'][118]['value'],response['body'][0]['counters'][119]['value'],response['body'][0]['counters'][120]['value']]
    mobiuz = [response['body'][0]['counters'][121]['value'],response['body'][0]['counters'][122]['value'],response['body'][0]['counters'][123]['value']]
    ucell = [response['body'][0]['counters'][124]['value'],response['body'][0]['counters'][125]['value'],response['body'][0]['counters'][126]['value']]
    uzmobile = [response['body'][0]['counters'][127]['value'],response['body'][0]['counters'][128]['value'],response['body'][0]['counters'][129]['value']]
    beeline_tas = [response['body'][0]['counters'][274]['value'], response['body'][0]['counters'][275]['value'], response['body'][0]['counters'][276]['value']]
    mobiuz_tas = [response['body'][0]['counters'][277]['value'], response['body'][0]['counters'][278]['value'], response['body'][0]['counters'][279]['value']]
    ucell_tas = [response['body'][0]['counters'][280]['value'], response['body'][0]['counters'][281]['value'], response['body'][0]['counters'][282]['value']]
    uzmobile_tas = [response['body'][0]['counters'][283]['value'], response['body'][0]['counters'][284]['value'], response['body'][0]['counters'][285]['value']]
    beeline_and = [response['body'][0]['counters'][286]['value'], response['body'][0]['counters'][287]['value'], response['body'][0]['counters'][289]['value']]
    mobiuz_and = [response['body'][0]['counters'][290]['value'], response['body'][0]['counters'][291]['value'], response['body'][0]['counters'][292]['value']]
    ucell_and = [response['body'][0]['counters'][293]['value'], response['body'][0]['counters'][294]['value'], response['body'][0]['counters'][295]['value']]
    uzmobile_and = [response['body'][0]['counters'][296]['value'], response['body'][0]['counters'][297]['value'], response['body'][0]['counters'][298]['value']]
    beeline_buh = [response['body'][0]['counters'][299]['value'], response['body'][0]['counters'][300]['value'],response['body'][0]['counters'][301]['value']]
    mobiuz_buh = [response['body'][0]['counters'][302]['value'], response['body'][0]['counters'][303]['value'],response['body'][0]['counters'][304]['value']]
    ucell_buh = [response['body'][0]['counters'][305]['value'], response['body'][0]['counters'][306]['value'],response['body'][0]['counters'][307]['value']]
    uzmobile_buh = [response['body'][0]['counters'][308]['value'], response['body'][0]['counters'][309]['value'],response['body'][0]['counters'][310]['value']]
    beeline_dji = [response['body'][0]['counters'][311]['value'], response['body'][0]['counters'][312]['value'],response['body'][0]['counters'][313]['value']]
    mobiuz_dji = [response['body'][0]['counters'][314]['value'], response['body'][0]['counters'][315]['value'],response['body'][0]['counters'][316]['value']]
    ucell_dji = [response['body'][0]['counters'][317]['value'], response['body'][0]['counters'][318]['value'],response['body'][0]['counters'][319]['value']]
    uzmobile_dji = [response['body'][0]['counters'][320]['value'], response['body'][0]['counters'][321]['value'],response['body'][0]['counters'][322]['value']]
    beeline_kas = [response['body'][0]['counters'][323]['value'], response['body'][0]['counters'][324]['value'],response['body'][0]['counters'][325]['value']]
    mobiuz_kas = [response['body'][0]['counters'][326]['value'], response['body'][0]['counters'][327]['value'],response['body'][0]['counters'][328]['value']]
    ucell_kas = [response['body'][0]['counters'][329]['value'], response['body'][0]['counters'][330]['value'],response['body'][0]['counters'][331]['value']]
    uzmobile_kas = [response['body'][0]['counters'][332]['value'], response['body'][0]['counters'][333]['value'],response['body'][0]['counters'][334]['value']]
    beeline_nav = [response['body'][0]['counters'][335]['value'], response['body'][0]['counters'][336]['value'],response['body'][0]['counters'][337]['value']]
    mobiuz_nav = [response['body'][0]['counters'][338]['value'], response['body'][0]['counters'][339]['value'],response['body'][0]['counters'][340]['value']]
    ucell_nav = [response['body'][0]['counters'][341]['value'], response['body'][0]['counters'][342]['value'],response['body'][0]['counters'][343]['value']]
    uzmobile_nav = [response['body'][0]['counters'][344]['value'], response['body'][0]['counters'][345]['value'],response['body'][0]['counters'][346]['value']]
    beeline_nam = [response['body'][0]['counters'][347]['value'], response['body'][0]['counters'][348]['value'],response['body'][0]['counters'][349]['value']]
    mobiuz_nam = [response['body'][0]['counters'][350]['value'], response['body'][0]['counters'][351]['value'],response['body'][0]['counters'][352]['value']]
    ucell_nam = [response['body'][0]['counters'][353]['value'], response['body'][0]['counters'][354]['value'],response['body'][0]['counters'][355]['value']]
    uzmobile_nam = [response['body'][0]['counters'][356]['value'], response['body'][0]['counters'][357]['value'],response['body'][0]['counters'][358]['value']]
    beeline_sam = [response['body'][0]['counters'][359]['value'], response['body'][0]['counters'][360]['value'],response['body'][0]['counters'][361]['value']]
    mobiuz_sam = [response['body'][0]['counters'][362]['value'], response['body'][0]['counters'][363]['value'],response['body'][0]['counters'][364]['value']]
    ucell_sam = [response['body'][0]['counters'][365]['value'], response['body'][0]['counters'][366]['value'],response['body'][0]['counters'][367]['value']]
    uzmobile_sam = [response['body'][0]['counters'][368]['value'], response['body'][0]['counters'][369]['value'],response['body'][0]['counters'][370]['value']]
    beeline_sur = [response['body'][0]['counters'][371]['value'], response['body'][0]['counters'][372]['value'],response['body'][0]['counters'][373]['value']]
    mobiuz_sur = [response['body'][0]['counters'][374]['value'], response['body'][0]['counters'][375]['value'],response['body'][0]['counters'][376]['value']]
    ucell_sur = [response['body'][0]['counters'][377]['value'], response['body'][0]['counters'][378]['value'],response['body'][0]['counters'][379]['value']]
    uzmobile_sur = [response['body'][0]['counters'][380]['value'], response['body'][0]['counters'][381]['value'],response['body'][0]['counters'][382]['value']]
    beeline_sir = [response['body'][0]['counters'][383]['value'], response['body'][0]['counters'][384]['value'],response['body'][0]['counters'][385]['value']]
    mobiuz_sir = [response['body'][0]['counters'][386]['value'], response['body'][0]['counters'][387]['value'],response['body'][0]['counters'][388]['value']]
    ucell_sir = [response['body'][0]['counters'][389]['value'], response['body'][0]['counters'][390]['value'],response['body'][0]['counters'][391]['value']]
    uzmobile_sir = [response['body'][0]['counters'][392]['value'], response['body'][0]['counters'][393]['value'],response['body'][0]['counters'][394]['value']]
    beeline_sir = [response['body'][0]['counters'][383]['value'], response['body'][0]['counters'][384]['value'],response['body'][0]['counters'][385]['value']]
    mobiuz_sir = [response['body'][0]['counters'][386]['value'], response['body'][0]['counters'][387]['value'],response['body'][0]['counters'][388]['value']]
    ucell_sir = [response['body'][0]['counters'][389]['value'], response['body'][0]['counters'][390]['value'],response['body'][0]['counters'][391]['value']]
    uzmobile_sir = [response['body'][0]['counters'][392]['value'], response['body'][0]['counters'][393]['value'],response['body'][0]['counters'][394]['value']]
    beeline_taso = [response['body'][0]['counters'][395]['value'], response['body'][0]['counters'][396]['value'],response['body'][0]['counters'][397]['value']]
    mobiuz_taso = [response['body'][0]['counters'][398]['value'], response['body'][0]['counters'][399]['value'],response['body'][0]['counters'][400]['value']]
    ucell_taso = [response['body'][0]['counters'][401]['value'], response['body'][0]['counters'][402]['value'],response['body'][0]['counters'][403]['value']]
    uzmobile_taso = [response['body'][0]['counters'][404]['value'], response['body'][0]['counters'][405]['value'],response['body'][0]['counters'][406]['value']]
    beeline_fer = [response['body'][0]['counters'][407]['value'], response['body'][0]['counters'][408]['value'],response['body'][0]['counters'][409]['value']]
    mobiuz_fer = [response['body'][0]['counters'][410]['value'], response['body'][0]['counters'][411]['value'],response['body'][0]['counters'][412]['value']]
    ucell_fer = [response['body'][0]['counters'][413]['value'], response['body'][0]['counters'][414]['value'],response['body'][0]['counters'][415]['value']]
    uzmobile_fer = [response['body'][0]['counters'][416]['value'], response['body'][0]['counters'][417]['value'],response['body'][0]['counters'][418]['value']]
    beeline_hor = [response['body'][0]['counters'][419]['value'], response['body'][0]['counters'][420]['value'],response['body'][0]['counters'][421]['value']]
    mobiuz_hor = [response['body'][0]['counters'][422]['value'], response['body'][0]['counters'][423]['value'],response['body'][0]['counters'][424]['value']]
    ucell_hor = [response['body'][0]['counters'][425]['value'], response['body'][0]['counters'][426]['value'],response['body'][0]['counters'][427]['value']]
    uzmobile_hor = [response['body'][0]['counters'][428]['value'], response['body'][0]['counters'][429]['value'],response['body'][0]['counters'][430]['value']]
    beeline_kar = [response['body'][0]['counters'][431]['value'], response['body'][0]['counters'][432]['value'],response['body'][0]['counters'][433]['value']]
    mobiuz_kar = [response['body'][0]['counters'][434]['value'], response['body'][0]['counters'][435]['value'],response['body'][0]['counters'][436]['value']]
    ucell_kar = [response['body'][0]['counters'][437]['value'], response['body'][0]['counters'][438]['value'],response['body'][0]['counters'][439]['value']]
    uzmobile_kar = [response['body'][0]['counters'][440]['value'], response['body'][0]['counters'][441]['value'],response['body'][0]['counters'][442]['value']]
    beeline_nps_regions = [beeline_tas, beeline_and, beeline_buh, beeline_dji, beeline_kas, beeline_nav, beeline_nam, beeline_sam, beeline_sur, beeline_sir, beeline_taso, beeline_fer, beeline_hor, beeline_kar]
    ucell_nps_regions = [ucell_tas, ucell_and, ucell_buh, ucell_dji, ucell_kas, ucell_nav, ucell_nam, ucell_sam, ucell_sur, ucell_sir, ucell_taso, ucell_fer, ucell_hor, ucell_kar]
    mobiuz_nps_regions = [mobiuz_tas, mobiuz_and, mobiuz_buh, mobiuz_dji, mobiuz_kas, mobiuz_nav, mobiuz_nam, mobiuz_sam, mobiuz_sur, mobiuz_sir, mobiuz_taso, mobiuz_fer, mobiuz_hor, mobiuz_kar]
    uzmobile_nps_regions = [uzmobile_tas, uzmobile_and, uzmobile_buh, uzmobile_dji, uzmobile_kas, uzmobile_nav, uzmobile_nam, uzmobile_sam, uzmobile_sur, uzmobile_sir, uzmobile_taso, uzmobile_fer, uzmobile_hor, uzmobile_kar]

    context = {
        'beeline_nps_regions': beeline_nps_regions,
        'ucell_nps_regions': ucell_nps_regions,
        'uzmobile_nps_regions': uzmobile_nps_regions,
        'mobiuz_nps_regions': mobiuz_nps_regions,
        'main': main,
        'second': second,
        'ucell_dop': ucell_dop,
        'beeline_dop': beeline_dop,
        'uzmobile_dop': uzmobile_dop,
        'mobiuz_dop': mobiuz_dop,
        'ucell': response['body'][0]['counters'][1]['value'],
        'beeline': response['body'][0]['counters'][30]['value'],
        'mobiuz': response['body'][0]['counters'][59]['value'],
        'uzmobile': response['body'][0]['counters'][88]['value'],
        'mens': mens,
        'womans': womans,
        'y16_19': y16_19,
        'y20_24': y20_24,
        'y25_34': y25_34,
        'y35_44': y35_44,
        'y45_54': y45_54,
        'y55': y55,
        'center': center,
        'city': city,
        'pgt': pgt,
        'village': village,
        'work': work,
        'conversations': conversations,
        'calls': calls,
        'internet': internet,
        'sim1': sim1,
        'sim2': sim2,
        'month3': month3,
        'month6': month6,
        'month12': month12,
        'month36': month36,
        'month60': month60,
        'month120': month120,
        'beeline_nps': beeline,
        'mobiuz_nps': mobiuz,
        'uzmobile_nps': uzmobile,
        'ucell_nps': ucell,

    }
    print(response['body'][0]['counters'][124]['value'])
    print(context)
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