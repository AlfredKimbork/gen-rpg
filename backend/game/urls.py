from rest_framework.routers import DefaultRouter

from game.views import GameSessionViewSet

router = DefaultRouter()
router.register(
    r"sessions",
    GameSessionViewSet,
    basename="session",
)

urlpatterns = router.urls
