"""Column types shared across models."""

from sqlalchemy import BigInteger, Integer

# SQLite requires INTEGER PRIMARY KEY for reliable autoincrement; plain BIGINT does not.
BigIntPK = BigInteger().with_variant(Integer, "sqlite")
