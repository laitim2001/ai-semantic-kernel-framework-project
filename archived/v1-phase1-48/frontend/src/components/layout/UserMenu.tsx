// =============================================================================
// IPA Platform - UserMenu Component
// =============================================================================
// Sprint 73: Phase 19 - User Menu Dropdown
//
// User menu dropdown with profile, settings, and logout.
//
// Dependencies:
//   - useAuthStore (src/store/authStore.ts)
//   - Lucide React icons
// =============================================================================

import { useState, useRef, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { User, Settings, LogOut, ChevronDown } from 'lucide-react';
import { useAuthStore } from '@/store/authStore';
import { cn } from '@/lib/utils';

export function UserMenu() {
  const navigate = useNavigate();
  const [isOpen, setIsOpen] = useState(false);
  const menuRef = useRef<HTMLDivElement>(null);

  const { user, isAuthenticated, logout } = useAuthStore();

  // 點擊外部關閉
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (menuRef.current && !menuRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }

    if (isOpen) {
      document.addEventListener('mousedown', handleClickOutside);
    }

    return () => {
      document.removeEventListener('mousedown', handleClickOutside);
    };
  }, [isOpen]);

  // 處理登出
  const handleLogout = () => {
    logout();
    setIsOpen(false);
    navigate('/login');
  };

  // 處理設定
  const handleSettings = () => {
    setIsOpen(false);
    navigate('/settings');
  };

  // 處理個人資料
  const handleProfile = () => {
    setIsOpen(false);
    navigate('/settings'); // 導向設定頁（可增加 profile 頁）
  };

  // 取得顯示名稱
  const displayName = user?.fullName || user?.email?.split('@')[0] || 'Guest';
  const userInitial = displayName.charAt(0).toUpperCase();

  return (
    <div className="relative" ref={menuRef}>
      {/* Trigger Button */}
      <button
        onClick={() => setIsOpen(!isOpen)}
        className={cn(
          'flex items-center gap-2 px-2 py-1.5 rounded-lg transition-colors',
          'hover:bg-gray-100 focus:outline-none focus:ring-2 focus:ring-primary/20',
          isOpen && 'bg-gray-100'
        )}
      >
        {/* Avatar */}
        <div className="w-8 h-8 bg-primary/10 rounded-full flex items-center justify-center">
          {isAuthenticated ? (
            <span className="text-sm font-medium text-primary">{userInitial}</span>
          ) : (
            <User className="w-4 h-4 text-gray-600" />
          )}
        </div>

        {/* Name */}
        <span className="text-sm font-medium text-gray-700 max-w-[100px] truncate">
          {displayName}
        </span>

        {/* Chevron */}
        <ChevronDown
          className={cn(
            'w-4 h-4 text-gray-500 transition-transform',
            isOpen && 'rotate-180'
          )}
        />
      </button>

      {/* Dropdown Menu */}
      {isOpen && (
        <div className="absolute right-0 mt-2 w-56 bg-white rounded-lg shadow-lg border border-gray-200 py-1 z-50">
          {/* User Info */}
          {isAuthenticated && user && (
            <>
              <div className="px-4 py-3 border-b border-gray-100">
                <p className="text-sm font-medium text-gray-900 truncate">
                  {user.fullName || 'User'}
                </p>
                <p className="text-xs text-gray-500 truncate">{user.email}</p>
                <p className="text-xs text-gray-400 mt-1">
                  角色: {user.role === 'admin' ? '管理員' : '使用者'}
                </p>
              </div>

              {/* Menu Items */}
              <div className="py-1">
                <button
                  onClick={handleProfile}
                  className="w-full flex items-center gap-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
                >
                  <User className="w-4 h-4" />
                  <span>個人資料</span>
                </button>

                <button
                  onClick={handleSettings}
                  className="w-full flex items-center gap-3 px-4 py-2 text-sm text-gray-700 hover:bg-gray-50 transition-colors"
                >
                  <Settings className="w-4 h-4" />
                  <span>設定</span>
                </button>
              </div>

              {/* Logout */}
              <div className="border-t border-gray-100 py-1">
                <button
                  onClick={handleLogout}
                  className="w-full flex items-center gap-3 px-4 py-2 text-sm text-red-600 hover:bg-red-50 transition-colors"
                >
                  <LogOut className="w-4 h-4" />
                  <span>登出</span>
                </button>
              </div>
            </>
          )}

          {/* Guest Mode */}
          {!isAuthenticated && (
            <div className="py-1">
              <div className="px-4 py-2 text-sm text-gray-500">
                您目前以訪客身份使用
              </div>
              <button
                onClick={() => {
                  setIsOpen(false);
                  navigate('/login');
                }}
                className="w-full flex items-center gap-3 px-4 py-2 text-sm text-primary hover:bg-primary/5 transition-colors"
              >
                <User className="w-4 h-4" />
                <span>登入帳號</span>
              </button>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
