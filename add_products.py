from app import app, db, Product


with app.app_context():

    product1 = Product(
        name="iPhone",
        price=70000,
        image="iphone.jpg",
        description="Latest Apple smartphone",
        rating=4.7,
        category="Mobiles"
    )

    product2 = Product(
        name="Smart Watch",
        price=2999,
        image="watch.jpg",
        description="Track fitness and health",
        rating=4.6,
        category="Wearables"
    )

    product3 = Product(
        name="Laptop",
        price=55000,
        image="laptop.jpg",
        description="Powerful laptop for work and gaming",
        rating=4.5,
        category="Laptops"
    )


    db.session.add(product1)
    db.session.add(product2)
    db.session.add(product3)

    db.session.commit()


print("Products Added!")