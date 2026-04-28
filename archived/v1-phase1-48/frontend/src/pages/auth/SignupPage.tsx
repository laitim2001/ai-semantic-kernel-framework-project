// =============================================================================
// IPA Platform - Signup Page
// =============================================================================
// Sprint 71: S71-2 - Login/Signup Pages
// Phase 18: Authentication System
//
// Registration page with email/password/fullName form.
// Integrates with authStore for user registration.
//
// Dependencies:
//   - authStore (src/store/authStore)
//   - UI components (src/components/ui)
// =============================================================================

import { FC, useState, FormEvent } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useAuthStore } from '@/store/authStore';
import { Button } from '@/components/ui/Button';
import { Input } from '@/components/ui/Input';
import { Label } from '@/components/ui/Label';
import { Card, CardHeader, CardContent, CardFooter } from '@/components/ui/Card';
import { AlertCircle, Loader2, UserPlus } from 'lucide-react';

// =============================================================================
// Types
// =============================================================================

interface FormErrors {
  email?: string;
  password?: string;
  confirmPassword?: string;
  fullName?: string;
}

// =============================================================================
// Component
// =============================================================================

export const SignupPage: FC = () => {
  const navigate = useNavigate();
  const { register, isLoading, error, clearError } = useAuthStore();

  // Form state
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [fullName, setFullName] = useState('');
  const [formErrors, setFormErrors] = useState<FormErrors>({});

  // Validate form
  const validateForm = (): boolean => {
    const errors: FormErrors = {};

    if (!email) {
      errors.email = '請輸入電子郵件';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)) {
      errors.email = '請輸入有效的電子郵件格式';
    }

    if (!password) {
      errors.password = '請輸入密碼';
    } else if (password.length < 8) {
      errors.password = '密碼長度至少 8 個字元';
    } else if (!/(?=.*[a-z])(?=.*[A-Z])(?=.*\d)/.test(password)) {
      errors.password = '密碼需包含大小寫字母和數字';
    }

    if (!confirmPassword) {
      errors.confirmPassword = '請確認密碼';
    } else if (password !== confirmPassword) {
      errors.confirmPassword = '兩次輸入的密碼不一致';
    }

    // Full name is optional, but validate length if provided
    if (fullName && fullName.length > 100) {
      errors.fullName = '姓名長度不得超過 100 個字元';
    }

    setFormErrors(errors);
    return Object.keys(errors).length === 0;
  };

  // Handle form submission
  const handleSubmit = async (e: FormEvent) => {
    e.preventDefault();
    clearError();

    if (!validateForm()) {
      return;
    }

    const success = await register(email, password, fullName || undefined);
    if (success) {
      navigate('/dashboard', { replace: true });
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-gradient-to-br from-slate-100 to-slate-200 dark:from-slate-900 dark:to-slate-800 p-4">
      <div className="w-full max-w-md">
        {/* Logo/Title */}
        <div className="text-center mb-8">
          <h1 className="text-3xl font-bold text-slate-900 dark:text-white">
            IPA Platform
          </h1>
          <p className="text-slate-600 dark:text-slate-400 mt-2">
            智能流程自動化平台
          </p>
        </div>

        {/* Signup Card */}
        <Card className="shadow-lg">
          <CardHeader className="text-center">
            <h2 className="text-xl font-semibold">註冊新帳號</h2>
            <p className="text-sm text-muted-foreground">
              創建您的帳號以開始使用
            </p>
          </CardHeader>

          <form onSubmit={handleSubmit}>
            <CardContent className="space-y-4">
              {/* Server Error */}
              {error && (
                <div className="flex items-center gap-2 p-3 text-sm text-red-600 bg-red-50 dark:bg-red-900/20 rounded-md">
                  <AlertCircle className="h-4 w-4 flex-shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              {/* Full Name Field (Optional) */}
              <div className="space-y-2">
                <Label htmlFor="fullName">
                  姓名 <span className="text-muted-foreground">(選填)</span>
                </Label>
                <Input
                  id="fullName"
                  type="text"
                  placeholder="您的姓名"
                  value={fullName}
                  onChange={(e) => {
                    setFullName(e.target.value);
                    if (formErrors.fullName) {
                      setFormErrors((prev) => ({ ...prev, fullName: undefined }));
                    }
                  }}
                  error={!!formErrors.fullName}
                  disabled={isLoading}
                  autoComplete="name"
                  autoFocus
                />
                {formErrors.fullName && (
                  <p className="text-sm text-red-500">{formErrors.fullName}</p>
                )}
              </div>

              {/* Email Field */}
              <div className="space-y-2">
                <Label htmlFor="email">電子郵件</Label>
                <Input
                  id="email"
                  type="email"
                  placeholder="name@example.com"
                  value={email}
                  onChange={(e) => {
                    setEmail(e.target.value);
                    if (formErrors.email) {
                      setFormErrors((prev) => ({ ...prev, email: undefined }));
                    }
                  }}
                  error={!!formErrors.email}
                  disabled={isLoading}
                  autoComplete="email"
                />
                {formErrors.email && (
                  <p className="text-sm text-red-500">{formErrors.email}</p>
                )}
              </div>

              {/* Password Field */}
              <div className="space-y-2">
                <Label htmlFor="password">密碼</Label>
                <Input
                  id="password"
                  type="password"
                  placeholder="••••••••"
                  value={password}
                  onChange={(e) => {
                    setPassword(e.target.value);
                    if (formErrors.password) {
                      setFormErrors((prev) => ({ ...prev, password: undefined }));
                    }
                  }}
                  error={!!formErrors.password}
                  disabled={isLoading}
                  autoComplete="new-password"
                />
                {formErrors.password && (
                  <p className="text-sm text-red-500">{formErrors.password}</p>
                )}
                <p className="text-xs text-muted-foreground">
                  至少 8 個字元，需包含大小寫字母和數字
                </p>
              </div>

              {/* Confirm Password Field */}
              <div className="space-y-2">
                <Label htmlFor="confirmPassword">確認密碼</Label>
                <Input
                  id="confirmPassword"
                  type="password"
                  placeholder="••••••••"
                  value={confirmPassword}
                  onChange={(e) => {
                    setConfirmPassword(e.target.value);
                    if (formErrors.confirmPassword) {
                      setFormErrors((prev) => ({ ...prev, confirmPassword: undefined }));
                    }
                  }}
                  error={!!formErrors.confirmPassword}
                  disabled={isLoading}
                  autoComplete="new-password"
                />
                {formErrors.confirmPassword && (
                  <p className="text-sm text-red-500">{formErrors.confirmPassword}</p>
                )}
              </div>
            </CardContent>

            <CardFooter className="flex flex-col gap-4">
              {/* Submit Button */}
              <Button
                type="submit"
                className="w-full"
                disabled={isLoading}
              >
                {isLoading ? (
                  <>
                    <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                    註冊中...
                  </>
                ) : (
                  <>
                    <UserPlus className="mr-2 h-4 w-4" />
                    註冊
                  </>
                )}
              </Button>

              {/* Login Link */}
              <p className="text-sm text-center text-muted-foreground">
                已經有帳號？{' '}
                <Link
                  to="/login"
                  className="text-primary hover:underline font-medium"
                >
                  登入
                </Link>
              </p>
            </CardFooter>
          </form>
        </Card>

        {/* Footer */}
        <p className="text-center text-sm text-slate-500 mt-6">
          © 2026 IPA Platform. All rights reserved.
        </p>
      </div>
    </div>
  );
};

export default SignupPage;
