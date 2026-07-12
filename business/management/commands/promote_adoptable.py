"""
Django management command: promote_adoptable
手动触发"诊疗完成5天自动转待领养"任务。
也可用于 cron 定时调用。

用法:
    python manage.py promote_adoptable
"""
from django.core.management.base import BaseCommand

from business.tasks import auto_promote_to_adoptable


class Command(BaseCommand):
    help = '诊疗完成5天后宠物自动转待领养并上架领养大厅'

    def handle(self, *args, **options):
        result = auto_promote_to_adoptable()
        self.stdout.write(
            self.style.SUCCESS(result)
        )
