from django import template
from datetime import date

register = template.Library()

@register.filter
def get_item(dictionary, key):
    """辞書から指定したキーの値を取得"""
    if isinstance(dictionary, dict):
        return dictionary.get(key, [])
    return []

@register.filter  
def get_field_color(field_name):
    """分野名に応じて色を返すフィルター"""
    field_colors = {
        '作図': 'danger',      # 赤
        'ソフト作成': 'success',  # 緑
        '配線': 'warning',     # 黄
        'デバック': 'info',     # 青
        '現地工事': 'secondary', # グレー
        '制御盤': 'primary',    # 紫
    }
    return field_colors.get(field_name, 'secondary')

@register.filter
def is_schedule_on_date(schedule, date_info):
    """スケジュールが指定した日付にあるかチェック"""
    try:
        year, month, day = date_info.split(',')
        current_date = date(int(year), int(month), int(day))
        
        return schedule.start_date <= current_date <= schedule.end_date
    except (ValueError, AttributeError, TypeError):
        return False

@register.filter
def person_color_class(user):
    """ユーザーIDに応じて色クラスを返すフィルター"""
    if user and user.id:
        color_index = (user.id % 10) + 1  # 1-10の範囲
        return f'badge-person-{color_index}'
    return 'badge-person-1'