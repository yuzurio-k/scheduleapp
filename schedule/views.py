from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.http import JsonResponse
from django.db.models import Q
from django.views.decorators.cache import never_cache
from datetime import datetime, timedelta, date
import calendar
import json
from django.utils import timezone
from .forms import ProjectForm, ScheduleForm, FieldForm

# 祝日ライブラリ（任意）
try:
    import jpholiday
except Exception:
    jpholiday = None

# マネージャー権限チェックデコレーター
def require_manager(view_func):
    def wrapper(request, *args, **kwargs):
        if not request.user.is_manager and not request.user.is_superuser:
            messages.error(request, 'この機能を使用する権限がありません。')
            return redirect('schedule:project_list')
        return view_func(request, *args, **kwargs)
    return wrapper

from .models import Schedule, Project, Field
from accounts.models import CustomUser

# Create your views here.
@login_required
def index(request):
    """ダッシュボード"""
    user = request.user
    
    # 今日の予定取得
    today = timezone.localdate()
    today_schedules = Schedule.objects.filter(
        start_date__lte=today,
        end_date__gte=today
    ).select_related('project', 'field')

    # 権限に応じてフィルタリング
    if not (user.is_manager or user.is_superuser or user.is_viewer):
        today_schedules = today_schedules.filter(
            Q(project__created_by=user) | Q(project__assigned_to=user)
        )

    # ステータス更新
    for schedule in today_schedules:
        old_status = schedule.status
        schedule.update_status_by_date()
        if old_status != schedule.status:
            schedule.save()

    # 案件一覧（最新5件）
    if user.is_manager or user.is_superuser or user.is_viewer:
        projects = Project.objects.all().select_related('created_by', 'assigned_to').order_by('-created_at')[:5]
    else:
        projects = Project.objects.filter(
            Q(created_by=user) | Q(assigned_to=user)
        ).select_related('created_by', 'assigned_to').order_by('-created_at')[:5]

    # 最近のスケジュール（最新5件）
    recent_schedules = Schedule.objects.filter(
        start_date__lte=today + timedelta(days=7),
        end_date__gte=today - timedelta(days=7)
    ).select_related('project', 'field')
    if not (user.is_manager or user.is_superuser or user.is_viewer):
        recent_schedules = recent_schedules.filter(
            Q(project__created_by=user) | Q(project__assigned_to=user)
        )
    recent_schedules = recent_schedules.order_by('-start_date')[:5]

    return render(request, 'schedule/home.html', {
        'today_schedules': today_schedules,
        'projects': projects,
        'recent_schedules': recent_schedules,
    })

@login_required
@never_cache
def project_list(request):
    """案件一覧"""
    if request.user.is_manager or request.user.is_superuser:
        # マネージャーは全案件を表示（担当者フィルタがある場合は自分のみ）
        projects = Project.objects.all().select_related('created_by', 'assigned_to')
        
        # マネージャー向け担当者フィルタ
        assignee_filter = request.GET.get('assignee', 'all')
        if assignee_filter == 'me':
            projects = projects.filter(assigned_to=request.user)
        # 'all'の場合はフィルタしない（全員の案件を表示）
    elif request.user.is_viewer:
        # 閲覧者は全案件を表示（担当者フィルタは利用不可）
        projects = Project.objects.all().select_related('created_by', 'assigned_to')
        assignee_filter = 'all'  # 閲覧者には担当者フィルタは関係ない
    else:
        # 一般ユーザーは自分が作成または担当している案件のみ
        projects = Project.objects.filter(
            Q(created_by=request.user) | Q(assigned_to=request.user)
        ).select_related('created_by', 'assigned_to').distinct()
        assignee_filter = 'all'  # 一般ユーザーには関係ない
    
    # 完了状態フィルタ（初期値は進行中）
    status_filter = request.GET.get('status', 'active')
    if status_filter == 'completed':
        projects = projects.filter(is_completed=True)
    elif status_filter == 'active':
        projects = projects.filter(is_completed=False)
    # 'all' の場合はフィルタしない
    
    # ソート機能
    sort_by = request.GET.get('sort', 'name')
    if sort_by == 'assigned_to':
        projects = projects.order_by('assigned_to__last_name', 'assigned_to__first_name', 'assigned_to__username')
    elif sort_by == 'manufacturing_number':
        projects = projects.order_by('manufacturing_number')
    elif sort_by == 'due_date':
        projects = projects.order_by('due_date')
    elif sort_by == 'created_at':
        projects = projects.order_by('-created_at')
    elif sort_by == 'completed_at':
        projects = projects.order_by('-completed_at')
    else:
        projects = projects.order_by('name')
    
    # 各プロジェクトに色情報と削除可否情報を追加
    colors = ['#007bff', '#28a745', '#dc3545', '#ffc107', '#6f42c1', '#fd7e14', '#20c997', '#e83e8c', '#6c757d', '#17a2b8']
    for project in projects:
        assigned_color_index = (project.assigned_to.id % 10) if project.assigned_to else 0
        
        project.assigned_bg_color = colors[assigned_color_index]
        project.assigned_text_color = '#212529' if assigned_color_index == 3 else '#ffffff'  # 黄色の場合は黒文字
    
    return render(request, 'schedule/project_list.html', {
        'projects': projects,
        'current_sort': sort_by,
        'current_status': status_filter,
        'current_assignee': assignee_filter,
    })

@login_required
@never_cache
def project_create(request):
    """案件作成"""
    # 権限チェック（閲覧者は案件作成不可）
    if request.user.is_viewer:
        messages.error(request, '閲覧者権限では案件を作成できません。')
        return redirect('schedule:project_list')
    
    if request.method == 'POST':
        form = ProjectForm(request.POST, user=request.user)
        if form.is_valid():
            project = form.save(commit=False)
            project.created_by = request.user
            project.save()
            messages.success(request, f'案件「{project.name}」を作成しました。')
            return redirect('schedule:project_detail', pk=project.pk)
    else:
        form = ProjectForm(user=request.user)
    
    return render(request, 'schedule/project_create.html', {
        'form': form,
    })

@login_required
@never_cache
def project_detail(request, pk):
    """案件詳細"""
    project = get_object_or_404(Project, pk=pk)
    
    # 権限チェック（マネージャー、閲覧者または関係者のみ）
    if not (request.user.is_manager or request.user.is_superuser or request.user.is_viewer or
            project.created_by == request.user or project.assigned_to == request.user):
        messages.error(request, 'この案件にアクセスする権限がありません。')
        return redirect('schedule:project_list')
    
    # 関連するスケジュール取得
    schedules = Schedule.objects.filter(project=project).select_related('field').order_by('start_date')
    
    # 各スケジュールのステータス更新
    for schedule in schedules:
        old_status = schedule.status
        schedule.update_status_by_date()
        if old_status != schedule.status:
            schedule.save()
    
    # 未完了のスケジュール数をカウント
    incomplete_schedules = schedules.exclude(status='completed')
    incomplete_count = incomplete_schedules.count()
    
    return render(request, 'schedule/project_detail.html', {
        'project': project,
        'schedules': schedules,
        'incomplete_count': incomplete_count,
        'has_incomplete_schedules': incomplete_count > 0,
    })

@login_required
@never_cache
def project_edit(request, pk):
    """案件編集"""
    project = get_object_or_404(Project, pk=pk)
    
    # 権限チェック（マネージャーまたは作成者のみ、閲覧者は編集不可）
    if request.user.is_viewer or not (request.user.is_manager or request.user.is_superuser or project.created_by == request.user):
        messages.error(request, 'この案件を編集する権限がありません。')
        return redirect('schedule:project_detail', pk=project.pk)
    
    if request.method == 'POST':
        form = ProjectForm(request.POST, instance=project, user=request.user)
        if form.is_valid():
            form.save()
            messages.success(request, f'案件「{project.name}」を更新しました。')
            return redirect('schedule:project_detail', pk=project.pk)
    else:
        form = ProjectForm(instance=project, user=request.user)
    
    return render(request, 'schedule/project_edit.html', {
        'form': form,
    })

@login_required
@never_cache
def project_delete(request, pk):
    """案件削除"""
    project = get_object_or_404(Project, pk=pk)
    
    # 権限チェック（マネージャーまたは作成者のみ、閲覧者は削除不可）
    if request.user.is_viewer or not (request.user.is_manager or request.user.is_superuser or project.created_by == request.user):
        messages.error(request, 'この案件を削除する権限がありません。')
        return redirect('schedule:project_detail', pk=project.pk)
    
    # スケジュール存在チェック
    if project.has_schedules():
        messages.error(request, 'スケジュールが登録されている案件は削除できません。')
        return redirect('schedule:project_detail', pk=project.pk)
    
    if request.method == 'POST':
        project_name = project.name
        project.delete()
        messages.success(request, f'案件「{project_name}」を削除しました。')
        return redirect('schedule:project_list')
    
    return render(request, 'schedule/project_confirm_delete.html', {
        'project': project,
    })

@login_required
def project_complete_view(request, pk):
    """案件完了/未完了切り替え"""
    project = get_object_or_404(Project, pk=pk)
    
    # 権限チェック（作成者、担当者、マネージャー、スーパーユーザーのみ）
    if not (project.created_by == request.user or 
            project.assigned_to == request.user or 
            request.user.is_manager or 
            request.user.is_superuser):
        messages.error(request, 'この案件の完了状態を変更する権限がありません。')
        return redirect('schedule:project_detail', pk=project.pk)
    
    if request.method == 'POST':
        # 案件を完了する前に、関連するすべてのスケジュールが完了しているかチェック
        if not project.is_completed:  # 未完了から完了にする場合のみチェック
            incomplete_schedules = project.schedule_set.exclude(status='completed')
            
            # ステータスを更新してから再度チェック
            for schedule in incomplete_schedules:
                old_status = schedule.status
                schedule.update_status_by_date()
                if old_status != schedule.status:
                    schedule.save()
            
            # 再度未完了のスケジュールをチェック
            incomplete_schedules = project.schedule_set.exclude(status='completed')
            
            if incomplete_schedules.exists():
                incomplete_count = incomplete_schedules.count()
                messages.error(request, f'この案件には未完了のスケジュール（{incomplete_count}件）があります。すべてのスケジュールを完了してから案件を完了してください。')
                return redirect('schedule:project_detail', pk=project.pk)
        
        project.toggle_completion()
        action = '完了' if project.is_completed else '未完了に戻し'
        messages.success(request, f'案件「{project.name}」を{action}ました。')
        return redirect('schedule:project_detail', pk=project.pk)
    
    return render(request, 'schedule/project_confirm_complete.html', {
        'project': project,
    })

@login_required
@never_cache
def calendar_view(request):
    today = timezone.localdate()

    # フィルタリングパラメータ
    assigned_to_filter = request.GET.get('assigned_to', '')  # 担当者フィルタ
    project_filter = request.GET.get('project', '')  # 案件フィルタ
    project_search = request.GET.get('project_search', '')  # 案件検索テキスト

    # ▼ 表示モード：'month'（既定） or 'week'
    scope = request.GET.get('scope', 'month')

    if scope == 'week':
        # 週表示：start=YYYY-MM-DD を受け取る（無ければ today）
        start_str = request.GET.get('start')
        try:
            week_start = datetime.strptime(start_str, "%Y-%m-%d").date() if start_str else today
        except Exception:
            week_start = today
        week_end = week_start + timedelta(days=6)

        # この7日間に "かかる" スケジュール
        base_qs = Schedule.objects.filter(
            start_date__lte=week_end,
            end_date__gte=week_start
        ).select_related('project', 'project__created_by', 'project__assigned_to')\
         .order_by('project__assigned_to__last_name', 'project__assigned_to__first_name', 'project__assigned_to__username', 'project__name', 'start_date')

        if not (request.user.is_manager or request.user.is_superuser or request.user.is_viewer):
            base_qs = base_qs.filter(Q(project__created_by=request.user) | Q(project__assigned_to=request.user))
        
        # 担当者フィルタリング適用
        if assigned_to_filter:
            base_qs = base_qs.filter(project__assigned_to__id=assigned_to_filter)
        
        # 案件フィルタは全ユーザーが使用可能
        if project_filter:
            base_qs = base_qs.filter(project__id=project_filter)

        # 担当者の色分け情報を追加
        colors = ['#007bff', '#28a745', '#dc3545', '#ffc107', '#6f42c1', '#fd7e14', '#20c997', '#e83e8c', '#6c757d', '#17a2b8']
        
        # ステータス更新
        for s in base_qs:
            old = s.status
            s.update_status_by_date()
            if old != s.status:
                s.save()
            
            # 担当者の色情報を追加
            if s.project.assigned_to:
                assigned_color_index = (s.project.assigned_to.id % 10)
                s.assigned_bg_color = colors[assigned_color_index]
                s.assigned_text_color = '#212529' if assigned_color_index == 3 else '#ffffff'  # 黄色の場合は黒文字

        # 7日間を1行に（各セルへ曜日/祝日フラグを埋め込み）
        row = []
        for i in range(7):
            d = week_start + timedelta(days=i)
            flags = _flags_for_date(d)
            # ★ 日曜 or 祝日は予定を表示しない
            if flags["is_sun"] or flags["is_holiday"]:
                todays = []
            else:
                todays = [s for s in base_qs if s.start_date <= d <= s.end_date]
            row.append({"day": d.day, "date": d, "schedules": todays, **flags})
        calendar_cells = [row]


        # 月切替ボタン用：現在の"基準月"（週開始日の年月）
        year = week_start.year
        month = week_start.month
        month_name = calendar.month_name[month]

        # 週ナビゲーション
        prev_start = week_start - timedelta(days=7)
        next_start = week_start + timedelta(days=7)

        # フィルタ用のデータ
        users_for_filter = []
        projects_for_filter = []
        
        # 担当者フィルタは管理者・マネージャー・閲覧者のみ
        if (request.user.is_manager or request.user.is_superuser or request.user.is_viewer):
            from accounts.models import CustomUser
            # 担当者フィルタの選択肢：マネージャーと一般ユーザーのみ（スーパーユーザーと閲覧者は除外）
            users_for_filter = CustomUser.objects.filter(
                is_manager=True, is_superuser=False
            ).union(
                CustomUser.objects.filter(
                    is_manager=False, is_superuser=False, is_viewer=False
                )
            ).order_by('last_name', 'first_name', 'username')
        
        # 案件フィルタは全ユーザーが使用可能
        if request.user.is_manager or request.user.is_superuser or request.user.is_viewer:
            # 管理者系は全案件
            projects_for_filter = Project.objects.all().order_by('name')
        else:
            # 一般ユーザーは自分が関係する案件のみ
            projects_for_filter = Project.objects.filter(
                Q(created_by=request.user) | Q(assigned_to=request.user)
            ).order_by('name')

        context = {
            "is_week": True,
            "week_start": week_start,
            "week_end": week_end,
            "prev_start": prev_start,
            "next_start": next_start,

            "year": year, "month": month, "month_name": month_name,
            "calendar_cells": calendar_cells,
            "schedules": base_qs,

            # 月ナビ（"月表示へ戻る"先のため）
            "prev_year": year if month > 1 else year - 1,
            "prev_month": month - 1 if month > 1 else 12,
            "next_year": year if month < 12 else year + 1,
            "next_month": month + 1 if month < 12 else 1,

            "today": today,
            
            # フィルタ関連
            "users_for_filter": users_for_filter,
            "projects_for_filter": projects_for_filter,
            "current_assigned_to": assigned_to_filter,
            "current_project": project_filter,
            "current_project_search": project_search,
        }
        return render(request, 'schedule/calendar.html', context)

    # ===== ここから従来の月表示 =====
    year = int(request.GET.get('year', today.year))
    month = int(request.GET.get('month', today.month))

    first_day = date(year, month, 1)
    last_day = (date(year+1, 1, 1) - timedelta(days=1)) if month == 12 else (date(year, month+1, 1) - timedelta(days=1))

    base_qs = Schedule.objects.filter(start_date__lte=last_day, end_date__gte=first_day) \
        .select_related('project', 'project__created_by', 'project__assigned_to')\
        .order_by('project__assigned_to__last_name', 'project__assigned_to__first_name', 'project__assigned_to__username', 'project__name', 'start_date')
    if not (request.user.is_manager or request.user.is_superuser or request.user.is_viewer):
        base_qs = base_qs.filter(Q(project__created_by=request.user) | Q(project__assigned_to=request.user))
    
    # 担当者フィルタリング適用
    if assigned_to_filter:
        base_qs = base_qs.filter(project__assigned_to__id=assigned_to_filter)
    
    # 案件フィルタは全ユーザーが使用可能
    if project_filter:
        base_qs = base_qs.filter(project__id=project_filter)

    # 担当者の色分け情報を追加
    colors = ['#007bff', '#28a745', '#dc3545', '#ffc107', '#6f42c1', '#fd7e14', '#20c997', '#e83e8c', '#6c757d', '#17a2b8']
    # 担当者の色分け情報を追加
    colors = ['#007bff', '#28a745', '#dc3545', '#ffc107', '#6f42c1', '#fd7e14', '#20c997', '#e83e8c', '#6c757d', '#17a2b8']
    for s in base_qs:
        old = s.status
        s.update_status_by_date()
        if old != s.status:
            s.save()
        
        # 担当者の色情報を追加
        if s.project.assigned_to:
            assigned_color_index = (s.project.assigned_to.id % 10)
            s.assigned_bg_color = colors[assigned_color_index]
            s.assigned_text_color = '#212529' if assigned_color_index == 3 else '#ffffff'  # 黄色の場合は黒文字
        
        # 担当者の色情報を追加
        if s.project.assigned_to:
            assigned_color_index = (s.project.assigned_to.id % 10)
            s.assigned_bg_color = colors[assigned_color_index]
            s.assigned_text_color = '#212529' if assigned_color_index == 3 else '#ffffff'  # 黄色の場合は黒文字

    cal = calendar.Calendar(firstweekday=6)  # 日曜始まり
    weeks = []
    for week in cal.monthdatescalendar(year, month):
        row = []
        for d in week:
            flags = _flags_for_date(d)
            if d.month != month:
                row.append({"day": 0, "date": d, "schedules": [], **flags})
            else:
                # ★ 日曜 or 祝日は予定を表示しない
                if flags["is_sun"] or flags["is_holiday"]:
                    todays = []
                else:
                    todays = [s for s in base_qs if s.start_date <= d <= s.end_date]
                row.append({"day": d.day, "date": d, "schedules": todays, **flags})
        weeks.append(row)


    prev_month = 12 if month == 1 else month-1
    prev_year  = year-1 if month == 1 else year
    next_month = 1 if month == 12 else month+1
    next_year  = year+1 if month == 12 else year

    # フィルタ用のデータ
    users_for_filter = []
    projects_for_filter = []
    
    # 担当者フィルタは管理者・マネージャー・閲覧者のみ
    if (request.user.is_manager or request.user.is_superuser or request.user.is_viewer):
        from accounts.models import CustomUser
        # 担当者フィルタの選択肢：マネージャーと一般ユーザーのみ（スーパーユーザーと閲覧者は除外）
        users_for_filter = CustomUser.objects.filter(
            is_manager=True, is_superuser=False
        ).union(
            CustomUser.objects.filter(
                is_manager=False, is_superuser=False, is_viewer=False
            )
        ).order_by('last_name', 'first_name', 'username')
    
    # 案件フィルタは全ユーザーが使用可能
    if request.user.is_manager or request.user.is_superuser or request.user.is_viewer:
        # 管理者系は全案件
        projects_for_filter = Project.objects.all().order_by('name')
    else:
        # 一般ユーザーは自分が関係する案件のみ
        projects_for_filter = Project.objects.filter(
            Q(created_by=request.user) | Q(assigned_to=request.user)
        ).order_by('name')

    return render(request, 'schedule/calendar.html', {
        "is_week": False,
        "year": year, "month": month, "month_name": calendar.month_name[month],
        "calendar_cells": weeks,
        "schedules": base_qs,
        "prev_year": prev_year, "prev_month": prev_month,
        "next_year": next_year, "next_month": next_month,
        "today": today,
        
        # フィルタ関連
        "users_for_filter": users_for_filter,
        "projects_for_filter": projects_for_filter,
        "current_assigned_to": assigned_to_filter,
        "current_project": project_filter,
        "current_project_search": project_search,
    })

@login_required
def schedule_api(request):
    """スケジュールAPI（カレンダー用）"""
    if request.user.is_manager or request.user.is_superuser:
        # マネージャーとスーパーユーザーは全ユーザーのスケジュールを表示
        schedules = Schedule.objects.all().select_related('project', 'project__created_by', 'project__assigned_to')
    else:
        # 一般ユーザーは自分が作成または担当するスケジュールのみ表示
        schedules = Schedule.objects.filter(
            Q(project__created_by=request.user) | Q(project__assigned_to=request.user)
        ).select_related('project', 'project__created_by', 'project__assigned_to')
    
    events = []
    for schedule in schedules:
        # 各スケジュールのステータスを更新
        old_status = schedule.status
        schedule.update_status_by_date()
        if old_status != schedule.status:
            schedule.save()
        
        # ステータスに基づく色設定
        if schedule.status == 'completed':
            color = '#28a745'  # 緑
        elif schedule.status == 'in_progress':
            color = '#007bff'  # 青
        else:  # overdue
            color = '#dc3545'  # 赤
        
        events.append({
            'id': schedule.id,
            'title': f'{schedule.project.name} - {schedule.field.name}',
            'start': schedule.start_date.isoformat(),
            'end': (schedule.end_date + timedelta(days=1)).isoformat(),  # 終了日の翌日
            'color': color,
            'url': f'/schedule/schedule/{schedule.id}/',
        })
    
    return JsonResponse(events, safe=False)

@login_required
@never_cache
def schedule_create(request):
    """スケジュール作成"""
    # 権限チェック（閲覧者はスケジュール作成不可）
    if request.user.is_viewer:
        messages.error(request, '閲覧者権限ではスケジュールを作成できません。')
        return redirect('schedule:project_list')
    
    project_id = request.GET.get('project')
    
    if request.method == 'POST':
        project_id = request.POST.get('project')
        field_id = request.POST.get('field')
        start_date = request.POST.get('start_date')
        end_date = request.POST.get('end_date')
        description = request.POST.get('description', '')

        if project_id and field_id and start_date and end_date:
            try:
                project = Project.objects.get(id=project_id)
                field = Field.objects.get(id=field_id)
                
                # 日付文字列をdateオブジェクトに変換
                from datetime import datetime
                start_date_obj = datetime.strptime(start_date, '%Y-%m-%d').date()
                end_date_obj = datetime.strptime(end_date, '%Y-%m-%d').date()
                
                # 権限チェック（閲覧者はスケジュール追加不可）
                if request.user.is_viewer or not (request.user.is_manager or request.user.is_superuser or 
                        project.created_by == request.user or project.assigned_to == request.user):
                    messages.error(request, 'この案件にスケジュールを追加する権限がありません。')
                    return redirect('schedule:project_detail', pk=project.pk)
                
                schedule = Schedule.objects.create(
                    project=project,
                    field=field,
                    start_date=start_date_obj,
                    end_date=end_date_obj,
                    description=description
                )
                
                # ステータス更新
                schedule.update_status_by_date()
                schedule.save()
                
                messages.success(request, f'スケジュール「{schedule.field.name}」を作成しました。')
                return redirect('schedule:project_detail', pk=project.pk)
            except (Project.DoesNotExist, Field.DoesNotExist):
                messages.error(request, '案件または分野が見つかりません。')
            except ValueError:
                messages.error(request, '日付の形式が正しくありません。')
        else:
            messages.error(request, '全ての必須項目を入力してください。')

    # 案件一覧と分野一覧を取得
    if request.user.is_manager or request.user.is_superuser:
        projects = Project.objects.all().select_related('created_by', 'assigned_to')
    else:
        projects = Project.objects.filter(
            Q(created_by=request.user) | Q(assigned_to=request.user)
        ).select_related('created_by', 'assigned_to')
    
    fields = Field.objects.all()
    
    # 初期選択案件
    selected_project = None
    if project_id:
        try:
            selected_project = Project.objects.get(id=project_id)
        except Project.DoesNotExist:
            pass

    return render(request, 'schedule/schedule_form.html', {
        'projects': projects,
        'fields': fields,
        'selected_project': selected_project,
        'title': 'スケジュール作成',
    })

@login_required
@never_cache
def schedule_detail(request, pk):
    """スケジュール詳細"""
    schedule = get_object_or_404(Schedule, pk=pk)
    
    # 権限チェック（マネージャーまたは関係者のみ）
    if not (request.user.is_manager or request.user.is_superuser or 
            schedule.project.created_by == request.user or schedule.project.assigned_to == request.user):
        messages.error(request, 'このスケジュールにアクセスする権限がありません。')
        return redirect('schedule:project_list')
    
    # ステータス更新
    old_status = schedule.status
    schedule.update_status_by_date()
    if old_status != schedule.status:
        schedule.save()
    
    return render(request, 'schedule/schedule_detail.html', {
        'schedule': schedule,
    })

@login_required
@never_cache
def schedule_edit(request, pk):
    """スケジュール編集"""
    schedule = get_object_or_404(Schedule, pk=pk)
    
    # 権限チェック（マネージャーまたは関係者のみ、閲覧者は編集不可）
    if request.user.is_viewer or not (request.user.is_manager or request.user.is_superuser or 
            schedule.project.created_by == request.user or schedule.project.assigned_to == request.user):
        messages.error(request, 'このスケジュールを編集する権限がありません。')
        return redirect('schedule:project_detail', pk=schedule.project.pk)
    
    if request.method == 'POST':
        form = ScheduleForm(request.POST, instance=schedule, user=request.user)
        if form.is_valid():
            updated_schedule = form.save()
            # ステータス更新
            updated_schedule.update_status_by_date()
            updated_schedule.save()
            messages.success(request, f'スケジュール「{updated_schedule.field.name}」を更新しました。')
            return redirect('schedule:project_detail', pk=updated_schedule.project.pk)
    else:
        form = ScheduleForm(instance=schedule, user=request.user)
    
    return render(request, 'schedule/schedule_edit.html', {
        'form': form,
        'schedule': schedule,
    })

@login_required
@never_cache
def schedule_delete(request, pk):
    """スケジュール削除"""
    schedule = get_object_or_404(Schedule, pk=pk)
    
    # 権限チェック（マネージャーまたは関係者のみ、閲覧者は削除不可）
    if request.user.is_viewer or not (request.user.is_manager or request.user.is_superuser or 
            schedule.project.created_by == request.user or schedule.project.assigned_to == request.user):
        messages.error(request, 'このスケジュールを削除する権限がありません。')
        return redirect('schedule:schedule_detail', pk=schedule.pk)
    
    if request.method == 'POST':
        project_pk = schedule.project.pk
        schedule_name = f'{schedule.project.name} - {schedule.field.name}'
        schedule.delete()
        messages.success(request, f'スケジュール「{schedule_name}」を削除しました。')
        return redirect('schedule:project_detail', pk=project_pk)
    
    return render(request, 'schedule/schedule_confirm_delete.html', {
        'schedule': schedule,
    })

def _flags_for_date(d):
    """
    指定した日付について、曜日や祝日の情報をdict形式で返す
    """
    is_sun = (d.weekday() == 6)  # 日曜
    is_sat = (d.weekday() == 5)  # 土曜
    is_holiday = False

    # jpholiday が使える場合のみ祝日チェック
    if jpholiday:
        try:
            is_holiday = jpholiday.is_holiday(d)
        except:
            is_holiday = False
    
    return {
        "is_sun": is_sun,
        "is_sat": is_sat,
        "is_holiday": is_holiday,
    }

# 分野管理ビュー
@login_required
def field_list_view(request):
    """分野一覧表示"""
    fields = Field.objects.all().order_by('name')
    return render(request, 'schedule/field_list.html', {'fields': fields})

@login_required
@never_cache
def field_create_view(request):
    """分野作成"""
    if request.method == 'POST':
        form = FieldForm(request.POST)
        if form.is_valid():
            field = form.save(commit=False)
            field.created_by = request.user
            field.save()
            import uuid
            unique_id = str(uuid.uuid4())[:8]
            messages.success(request, f'分野を作成しました。({unique_id})')
            return redirect('schedule:field_list')
    else:
        form = FieldForm()
    
    return render(request, 'schedule/field_form.html', {
        'form': form,
        'title': '分野作成'
    })

@login_required
@never_cache
def field_edit_view(request, field_id):
    """分野編集"""
    field = get_object_or_404(Field, id=field_id)
    
    if request.method == 'POST':
        form = FieldForm(request.POST, instance=field)
        if form.is_valid():
            form.save()
            messages.success(request, '分野を更新しました。')
            return redirect('schedule:field_list')
    else:
        form = FieldForm(instance=field)
    
    return render(request, 'schedule/field_form.html', {
        'form': form,
        'title': '分野編集',
        'field': field
    })

@login_required
@never_cache
def field_delete_view(request, field_id):
    """分野削除"""
    field = get_object_or_404(Field, id=field_id)
    
    # 使用中の分野は削除できない
    if Schedule.objects.filter(field=field).exists():
        messages.error(request, 'この分野は使用中のため削除できません。')
        return redirect('schedule:field_list')
    
    if request.method == 'POST':
        field.delete()
        messages.success(request, '分野を削除しました。')
        return redirect('schedule:field_list')
    
    return render(request, 'schedule/field_confirm_delete.html', {'field': field})

@login_required
@never_cache
def schedule_complete_view(request, schedule_id):
    """スケジュール完了/未完了切替"""
    schedule = get_object_or_404(Schedule, id=schedule_id)
    
    # 権限チェック（マネージャーまたは関係者のみ）
    if not (request.user.is_manager or request.user.is_superuser or 
            schedule.project.created_by == request.user or schedule.project.assigned_to == request.user):
        messages.error(request, 'このスケジュールの完了状態を変更する権限がありません。')
        return redirect('schedule:project_detail', pk=schedule.project.pk)
    
    # スケジュールの状態を切替
    if schedule.status == 'completed':
        schedule.status = 'pending'  # または 'in_progress'
        schedule.completed_at = None
        action = '未完了に戻し'
    else:
        schedule.status = 'completed'
        schedule.completed_at = timezone.now()
        action = '完了に設定'
    
    schedule.save()
    messages.success(request, f'スケジュール「{schedule.field.name}」を{action}ました。')
    return redirect('schedule:project_detail', pk=schedule.project.pk)