from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from database import Base
from sqlalchemy import ForeignKey, String

class Application(Base):
    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(primary_key=True)
    company: Mapped[str] = mapped_column(String(100), nullable=False)
    role: Mapped[str] = mapped_column(String(100), nullable=False)
    status: Mapped[str] = mapped_column(String(20), nullable=False)
    priority: Mapped[str] = mapped_column(String(10), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable = False)

class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique = True, index = True, nullable = False)
    hashed_password: Mapped[str] = mapped_column(String(255), nullable = False)

