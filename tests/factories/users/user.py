import factory

from django.contrib.auth import get_user_model

from faker import Faker

fake = Faker()


class User(factory.django.DjangoModelFactory):
    """
    User Factory
    """

    class Meta:
        model = get_user_model()

    email = factory.Sequence(
        lambda o: f"{fake.first_name()}{fake.last_name()}{o}@{fake.free_email_domain()}".lower()
    )
    username = factory.Sequence(lambda o: f"{fake.user_name()}{o}")
    first_name = factory.LazyAttribute(lambda o: fake.first_name())
    last_name = factory.LazyAttribute(lambda o: fake.last_name())

    is_superuser = False

    @factory.post_generation
    def password(self, create, extracted, **kwargs):
        raw_password = extracted or "SamplePassword"
        self.set_password(raw_password)
        if create:
            self.save(update_fields=["password"])
