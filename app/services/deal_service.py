def calculate_discount(old_price, new_price):

    if not old_price or old_price <= new_price:
        return 0


    discount = (
        (old_price - new_price)
        / old_price
    ) * 100


    return round(discount, 2)



def is_deal(old_price, new_price):

    discount = calculate_discount(
        old_price,
        new_price
    )


    if discount >= 15:
        return True


    return False
