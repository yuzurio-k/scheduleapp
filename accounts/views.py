from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.paginator import Paginator
from django.views.decorators.cache import never_cache
from django.views.decorators.csrf import csrf_protect
from django.http import HttpResponseRedirect
from django.urls import reverse
from .forms import CustomUserCreationForm, UserManagementForm, UserProfileForm, PasswordChangeForm
from .decorators import manager_required
from django.contrib.auth import update_session_auth_hash

User = get_user_model()

def signup(request):
    """ユーザー登録"""
    if request.method == 'POST':
        form = CustomUserCreationForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, 'アカウントが作成されました。')
            return redirect('schedule:index')
    else:
        form = CustomUserCreationForm()
    
    return render(request, 'registration/signup.html', {'form': form})

@manager_required
def user_list(request):
    """ユーザー一覧（マネージャー専用）"""
    users = User.objects.all().order_by('username')
    
    # 検索機能
    search = request.GET.get('search')
    if search:
        users = users.filter(
            username__icontains=search
        ) | users.filter(
            email__icontains=search
        ) | users.filter(
            department__icontains=search
        )
    
    # ページネーション
    paginator = Paginator(users, 20)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    context = {
        'page_obj': page_obj,
        'search': search,
    }
    return render(request, 'accounts/user_list.html', context)

@manager_required
def user_create(request):
    """ユーザー作成（マネージャー専用）"""
    if request.method == 'POST':
        form = UserManagementForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            # デフォルトパスワードを設定
            user.set_password('temp123')  # 初期パスワード
            user.save()
            messages.success(request, f'ユーザー「{user.username}」が作成されました。初期パスワード: temp123')
            return redirect('accounts:user_list')
    else:
        form = UserManagementForm()
    
    return render(request, 'accounts/user_form.html', {'form': form, 'title': 'ユーザー作成'})

@manager_required
def user_edit(request, user_id):
    """ユーザー編集（マネージャー専用）"""
    user = get_object_or_404(User, id=user_id)
    
    if request.method == 'POST':
        form = UserManagementForm(request.POST, instance=user)
        if form.is_valid():
            form.save()
            messages.success(request, f'ユーザー「{user.username}」が更新されました。')
            return redirect('accounts:user_list')
    else:
        form = UserManagementForm(instance=user)
    
    return render(request, 'accounts/user_form.html', {'form': form, 'title': 'ユーザー編集', 'user': user})

@manager_required
def user_delete(request, user_id):
    """ユーザー削除（マネージャー専用）"""
    user = get_object_or_404(User, id=user_id)
    
    if request.user == user:
        messages.error(request, '自分自身を削除することはできません。')
        return redirect('accounts:user_list')
    
    if request.method == 'POST':
        username = user.username
        user.delete()
        messages.success(request, f'ユーザー「{username}」が削除されました。')
        return redirect('accounts:user_list')
    
    return render(request, 'accounts/user_confirm_delete.html', {'user': user})

@login_required
@never_cache
def profile(request):
    """プロフィール表示・編集"""
    if request.method == 'POST':
        if request.user.is_manager or request.user.is_superuser:
            # マネージャーは全フィールド編集可能
            form = UserManagementForm(request.POST, instance=request.user)
        else:
            # 一般ユーザーは基本情報のみ編集可能
            form = UserProfileForm(request.POST, instance=request.user)
            
        if form.is_valid():
            form.save()
            messages.success(request, 'プロフィールを更新しました。')
            return redirect('accounts:profile')
    else:
        if request.user.is_manager or request.user.is_superuser:
            form = UserManagementForm(instance=request.user)
            # スーパーユーザー以外は自分のis_activeを変更できないようにする
            if not request.user.is_superuser:
                form.fields['is_active'].widget.attrs['disabled'] = True
        else:
            form = UserProfileForm(instance=request.user)
    
    return render(request, 'accounts/profile.html', {'form': form})

@never_cache
def custom_logout(request):
    """カスタムログアウト処理"""
    if request.method == 'POST':
        logout(request)
        messages.success(request, 'ログアウトしました。')
        # キャッシュをクリアするためのレスポンス
        response = HttpResponseRedirect(reverse('login'))
        response['Cache-Control'] = 'no-cache, no-store, must-revalidate'
        response['Pragma'] = 'no-cache'
        response['Expires'] = '0'
        return response
    else:
        # GETリクエストの場合はログアウト確認画面を表示
        return render(request, 'registration/logout_confirm.html')

@login_required
@never_cache
def password_change_view(request):
    """パスワード変更"""
    if request.method == 'POST':
        form = PasswordChangeForm(user=request.user, data=request.POST)
        if form.is_valid():
            form.save()
            update_session_auth_hash(request, request.user)  # セッションを維持
            messages.success(request, 'パスワードを変更しました。')
            return redirect('accounts:profile')
    else:
        form = PasswordChangeForm(user=request.user)
    
    return render(request, 'accounts/password_change.html', {'form': form})
