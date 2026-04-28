from django.db import models
import uuid

# 1. Tabel Master
class Role(models.Model):
    role_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role_name = models.CharField(unique=True, max_length=50)

    class Meta:
        managed = False
        db_table = '"TikTakTuk"."role"'

class UserAccount(models.Model):
    user_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(unique=True, max_length=100)
    password = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = '"TikTakTuk"."user_account"'

# 2. Tabel Relasi/Junction
class AccountRole(models.Model):
    # Menggunakan user_id sebagai primary_key di Django karena Django ORM kurang 
    # mendukung composite primary key secara bawaan, namun ini aman untuk operasi kita.
    user = models.OneToOneField(UserAccount, on_delete=models.CASCADE, db_column='user_id', primary_key=True)
    role = models.ForeignKey(Role, on_delete=models.RESTRICT, db_column='role_id')

    class Meta:
        managed = False
        db_table = '"TikTakTuk"."account_role"'

# 3. Tabel Profil Spesifik
class Customer(models.Model):
    customer_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    full_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20, null=True, blank=True)
    user = models.OneToOneField(UserAccount, on_delete=models.CASCADE, db_column='user_id')

    class Meta:
        managed = False
        db_table = '"TikTakTuk"."customer"'

class Organizer(models.Model):
    organizer_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    organizer_name = models.CharField(max_length=100)
    contact_email = models.CharField(max_length=100, null=True, blank=True)
    user = models.OneToOneField(UserAccount, on_delete=models.CASCADE, db_column='user_id')

    class Meta:
        managed = False
        db_table = '"TikTakTuk"."organizer"'