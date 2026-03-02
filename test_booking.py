import asyncio
from sqlmodel import select
from db import get_session
from models import Order, OrderStatus, ShoppingCart, User

async def main():
    async for session in get_session():
        print("Checking users...")
        users = (await session.execute(select(User))).scalars().all()
        if not users:
            print("No users found. Please create one.")
            return
        user = users[0]
        print(f"Using test user: {user.email}")
        
        # Give user a cart item
        cart = (await session.execute(select(ShoppingCart).where(ShoppingCart.user_id == user.id))).scalars().first()
        if not cart:
            cart = ShoppingCart(user_id=user.id)
            session.add(cart)
        
        cart.items = [{"name": "Test Booking Item", "quantity": 1, "price": 999, "product_id": "test-id"}]
        session.add(cart)
        await session.commit()
        print("Cart seeded.")
        
        # Create Booking
        booking = Order(
            user_id=user.id,
            total_amount=999.0,
            status=OrderStatus.REQUESTED,
            items=cart.items,
            shipping_address={"firstName": "Test", "lastName": "User", "address": "123 Test St", "city": "Test City", "pincode": "123456", "email": user.email, "phone": "1234567890"},
        )
        session.add(booking)
        await session.commit()
        print(f"Booking {booking.id} created successfully with status {booking.status}.")
        break
        
if __name__ == "__main__":
    asyncio.run(main())
