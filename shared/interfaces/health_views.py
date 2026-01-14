"""
Health check views.
"""
from django.db import connection
from django.core.cache import cache
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView


class HealthCheckView(APIView):
    """Basic health check endpoint."""
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({'status': 'healthy'}, status=status.HTTP_200_OK)


class ReadinessCheckView(APIView):
    """Readiness probe - checks all dependencies."""
    permission_classes = [AllowAny]

    def get(self, request):
        checks = {
            'database': self._check_database(),
            'cache': self._check_cache(),
        }

        all_healthy = all(check['healthy'] for check in checks.values())
        status_code = status.HTTP_200_OK if all_healthy else status.HTTP_503_SERVICE_UNAVAILABLE

        return Response(
            {
                'status': 'ready' if all_healthy else 'not_ready',
                'checks': checks,
            },
            status=status_code,
        )

    def _check_database(self):
        try:
            with connection.cursor() as cursor:
                cursor.execute('SELECT 1')
            return {'healthy': True}
        except Exception as e:
            return {'healthy': False, 'error': str(e)}

    def _check_cache(self):
        try:
            cache.set('health_check', 'ok', 10)
            value = cache.get('health_check')
            return {'healthy': value == 'ok'}
        except Exception as e:
            return {'healthy': False, 'error': str(e)}


class LivenessCheckView(APIView):
    """Liveness probe - basic application check."""
    permission_classes = [AllowAny]

    def get(self, request):
        return Response({'status': 'alive'}, status=status.HTTP_200_OK)
