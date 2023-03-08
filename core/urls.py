from django.contrib.staticfiles.views import serve
from django.urls import path, re_path
from .views import *

app_name = 'core'

urlpatterns = [
    path('dashboards', dashboards, name='dashboard'),
    path('', home, name='home'),
    path('filter/<str:ctg>/<str:ctg2>', home1, name='home1'),
    path('checkout/', CheckoutView.as_view(), name='checkout'),
    path('order-summary/', order_summary, name='order-summary'),
    path('product/<slug>/', detail, name='product'),
    path('add-to-cart/<slug>', add_to_cart, name='add-to-cart'),
    path('add-to-cart1', add_to_cart1, name='add-to-cart1'),
    path('add-coupon/', AddCouponView.as_view(), name='add-coupon'),
    path('remove-from-cart/<slug>/', remove_from_cart, name='remove-from-cart'),
    path('remove-item-from-cart/<slug>/', remove_single_item_from_cart,
         name='remove-single-item-from-cart'),
    # path('payment/<payment_option>/', PaymentView.as_view(), name='payment'),
    path('successPayment/', SuccesPayment, name='success'),
    path('request-refund/', RequestRefundView.as_view(), name='request-refund'),
]