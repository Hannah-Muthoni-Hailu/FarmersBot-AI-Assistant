from backend.database.database import engine
from backend.database.models import Base

Base.metadata.create_all(bind=engine)