from django.db import models
import uuid


class UserAccount(models.Model):
    user_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    username = models.CharField(unique=True, max_length=100)
    password = models.CharField(max_length=255)

    class Meta:
        managed = False
        db_table = "user_account"


class Role(models.Model):
    role_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    role_name = models.CharField(unique=True, max_length=50)

    class Meta:
        managed = False
        db_table = "role"


class AccountRole(models.Model):
    role = models.ForeignKey(Role, models.RESTRICT, db_column="role_id")
    user = models.ForeignKey(UserAccount, models.CASCADE, db_column="user_id")
    pk = models.CompositePrimaryKey("role", "user")

    class Meta:
        managed = False
        db_table = "account_role"
        # Constraint: Each user can have only 1 role (1:n relationship)
        constraints = [
            models.UniqueConstraint(
                fields=["user_id"],
                name="one_role_per_user",
                violation_error_message="Setiap user hanya boleh memiliki 1 role",
            )
        ]


class Customer(models.Model):
    customer_id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    full_name = models.CharField(max_length=100)
    phone_number = models.CharField(max_length=20, blank=True, null=True)
    user = models.OneToOneField(UserAccount, models.CASCADE, db_column="user_id")

    class Meta:
        managed = False
        db_table = "customer"


class Organizer(models.Model):
    organizer_id = models.UUIDField(
        primary_key=True, default=uuid.uuid4, editable=False
    )
    organizer_name = models.CharField(max_length=100)
    contact_email = models.CharField(max_length=100, blank=True, null=True)
    user = models.OneToOneField(UserAccount, models.CASCADE, db_column="user_id")

    class Meta:
        managed = False
        db_table = "organizer"
