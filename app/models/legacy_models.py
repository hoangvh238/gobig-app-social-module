from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import String, Integer


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str | None] = mapped_column(String)
    email: Mapped[str | None] = mapped_column(String)
    avatar_id: Mapped[int | None] = mapped_column(Integer)
    follower_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    following_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    recipe_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    streak_hash: Mapped[str | None] = mapped_column(String)


class Recipe(Base):
    __tablename__ = "recipes"
    __table_args__ = {"extend_existing": True}

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    title: Mapped[str | None] = mapped_column(String)
    slug: Mapped[str | None] = mapped_column(String)
    status: Mapped[str | None] = mapped_column(String)
    author_id: Mapped[int | None] = mapped_column(Integer)
    like_count: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
