from django.db.models.signals import post_save
from django.conf import settings
from django.db import models
from django.http import request
from django.shortcuts import reverse, get_object_or_404
from django.utils import timezone
from django_countries.fields import CountryField

ADDRESS_CHOICES = (
    ('B', 'Billing'),
    ('S', 'Shipping'),
)


class SubCategory(models.Model):
    title = models.CharField(max_length=16)

    def __str__(self):
        return self.title


class Category(models.Model):
    title = models.CharField(max_length=30)
    subcategory = models.ForeignKey(SubCategory, on_delete=models.CASCADE, default=None)

    def __str__(self):
        return self.title + " " + self.subcategory.title


class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    stripe_customer_id = models.CharField(max_length=50, blank=True, null=True)
    one_click_purchasing = models.BooleanField(default=False)
    image = models.ImageField(default=None)

    def __str__(self):
        return self.user.username


class Brand(models.Model):
    title = models.CharField(max_length=15)
    category = models.ForeignKey(Category, null=True, on_delete=models.CASCADE, default=None)

    def __str__(self):
        return self.title


class Item(models.Model):
    acrtiul = models.TextField(max_length=100, default="NONE")
    title = models.CharField(max_length=100)
    price = models.FloatField()
    discount_price = models.FloatField(blank=True, null=True)
    category = models.ForeignKey(Category, on_delete=models.CASCADE, default=None)
    slug = models.SlugField()
    description = models.TextField(default="NONE")
    description1 = models.TextField(default="NONE")
    description2 = models.TextField(default="NONE")
    image = models.ImageField()

    def __str__(self):
        return self.title

    def get_price(self):
        return int(self.price)

    def get_absolute_url(self):
        return reverse("core:product", kwargs={
            'slug': self.slug
        })

    def get_add_to_cart_url(self, user):
        item = get_object_or_404(Item, slug=self.slug)
        order_item, created = OrderItem.objects.get_or_create(
            item=item,
            user=request.user,
            ordered=False

        )
        order_qs = Order.objects.filter(user=user, payment=False)
        if order_qs.exists():
            order = order_qs[0]
            # check if the order item is in the order
            if order.items.filter(item__slug=item.slug).exists():
                order_item.quantity += 1
                order_item.save()
                # messages.info(request, "This item quantity was updated.")
                # return redirect("core:order-summary")
            else:
                order.items.add(order_item)
                # messages.info(request, "This item was added to your cart.")
                # return redirect("core:order-summary")
        else:
            ordered_date = timezone.now()
            order = Order.objects.create(
                user=request.user, ordered_date=ordered_date)
            order.items.add(order_item)
            # messages.info(request, "This item was added to your cart.")
        # return redirect("core:order-summary")
        # return reverse("core:add-to-cart", kwargs={
        #     'slug': self.slug
        # })

    def get_remove_from_cart_url(self):
        return reverse("core:remove-from-cart", kwargs={
            'slug': self.slug
        })


class OrderItem(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,
                             on_delete=models.CASCADE)
    ordered = models.BooleanField(default=False)
    item = models.ForeignKey(Item, on_delete=models.CASCADE)
    quantity = models.IntegerField(default=1)

    def __str__(self):
        return f"{self.quantity} of {self.item.title}"

    def get_total_item_price(self):
        return self.quantity * self.item.price

    def get_total_discount_item_price(self):
        return self.quantity * self.item.discount_price

    def get_amount_saved(self):
        return self.get_total_item_price() - self.get_total_discount_item_price()

    def get_final_price(self):
        if self.item.discount_price:
            return self.get_total_discount_item_price()
        return self.get_total_item_price()


class Order(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    ref_code = models.CharField(max_length=20, null=True)
    items = models.ManyToManyField(OrderItem)
    start_date = models.DateTimeField(auto_now_add=True)
    ordered_date = models.DateTimeField()
    shipping_address = models.ForeignKey(
        'Address', related_name='shipping_address', on_delete=models.SET_NULL, null=True)
    payment = models.BooleanField(default=False)
    coupon = models.ForeignKey(
        'Coupon', on_delete=models.SET_NULL, null=True, default=None)
    being_delivered = models.BooleanField(default=False)
    received = models.BooleanField(default=False)
    refund_requested = models.BooleanField(default=False)
    refund_granted = models.BooleanField(default=False)
    v_obrabotke = models.BooleanField(default=False)
    def __str__(self):
        if self.payment == True:
            if self.v_obrabotke == True:
                return "Номер заказа: " + str(self.id) + " Оплачено. В обработке"
            return "Номер заказа: " + str(self.id) + " Оплачено. Не обработано"
        return self.user.username + ". Номер заказа: " + str(self.id) + " Не оплачено"


    def get_total(self):
        total = 0
        for order_item in self.items.all():
            total += order_item.get_final_price()
        if self.coupon:
            total -= self.coupon.amount
        return int(total)


class Address(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
    street_address = models.CharField(max_length=100, null=True)
    comments = models.CharField(max_length=255, null=True)
    phone_number = models.CharField(max_length=50)

    def __str__(self):
        return self.user.username

    class Meta:
        verbose_name_plural = 'Addresses'


class Coupon(models.Model):
    code = models.CharField(max_length=15)
    amount = models.FloatField()

    def __str__(self):
        return self.code


class Refund(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE)
    reason = models.TextField()
    accepted = models.BooleanField(default=False)
    email = models.EmailField()

    def __str__(self):
        return f"{self.pk}"


def userprofile_receiver(sender, instance, created, *args, **kwargs):
    if created:
        userprofile = UserProfile.objects.create(user=instance)


post_save.connect(userprofile_receiver, sender=settings.AUTH_USER_MODEL)
