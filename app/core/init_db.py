from app.core.database.helper import engine
from app.core.models import Base
Base.metadata.create_all(bind=engine)
# если база пустая то запустить отдельно