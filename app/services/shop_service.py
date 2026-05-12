import logging
from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from app.db.models import Product, Order

logger = logging.getLogger(__name__)

async def get_active_products(session: AsyncSession):
    """Sotuvdagi faol kurslar va treninglarni olish."""
    try:
        result = await session.execute(select(Product).where(Product.is_active == True))
        return result.scalars().all()
    except Exception as e:
        logger.error(f"Failed to get products: {e}")
        return []

async def get_product_by_id(session: AsyncSession, product_id: int):
    """Kurs ma'lumotlarini ID orqali olish."""
    try:
        result = await session.execute(select(Product).where(Product.id == product_id))
        return result.scalar_one_or_none()
    except Exception as e:
        logger.error(f"Failed to get product {product_id}: {e}")
        return None

async def create_order(session: AsyncSession, user_id: int, product_id: int, amount: int):
    """Yangi buyurtma yaratish."""
    try:
        order = Order(
            user_id=user_id,
            product_id=product_id,
            amount=amount,
            status="pending"
        )
        session.add(order)
        await session.commit()
        await session.refresh(order)
        return order
    except Exception as e:
        logger.error(f"Failed to create order: {e}")
        await session.rollback()
        return None

async def update_order_status(session: AsyncSession, order_id: int, status: str):
    """Buyurtma holatini yangilash (masalan, 'paid')."""
    try:
        await session.execute(
            update(Order)
            .where(Order.id == order_id)
            .values(status=status)
        )
        await session.commit()
        return True
    except Exception as e:
        logger.error(f"Failed to update order status: {e}")
        await session.rollback()
        return False
