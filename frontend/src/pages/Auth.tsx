import React, { useState } from 'react';
import { LuGraduationCap, LuUserRound } from 'react-icons/lu';
import { Link, useNavigate } from '../lib/router';
import { useI18n } from '../lib/i18n';
import { useAuth } from '../lib/auth';
import { errorMessage, LANGUAGES, type Language, type Role } from '../lib/api';
import { Logo } from '../components/Logo';
import { LanguageSwitcher } from '../components/LanguageSwitcher';
import { Button, Field, Input, Select, ErrorState, cn } from '../components/ui';
import { ServiceBanner } from '../lib/status';

function AuthLayout({ title, subtitle, children, footer }: { title: string; subtitle: string; children: React.ReactNode; footer: React.ReactNode }) {
  return (
    <div className="surface-glow flex min-h-screen flex-col">
      <header className="mx-auto flex w-full max-w-6xl items-center justify-between px-4 py-4 sm:px-6">
        <Link to="/" aria-label="EdNova AI">
          <Logo />
        </Link>
        <LanguageSwitcher />
      </header>
      <main className="flex flex-1 items-center justify-center px-4 pb-12">
        <div className="w-full max-w-md animate-rise">
          <div className="mb-4 empty:hidden">
            <ServiceBanner compact />
          </div>
          <div className="panel-elevated p-6 sm:p-8">
            <h1 className="display text-3xl text-ink">{title}</h1>
            <p className="mt-2 text-sm text-ink-soft">{subtitle}</p>
            <div className="mt-6">{children}</div>
          </div>
          <p className="mt-4 text-center text-sm text-ink-soft">{footer}</p>
        </div>
      </main>
    </div>
  );
}

export function Login() {
  const { t } = useI18n();
  const { login } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    setPending(true);
    setError(null);
    try {
      const u = await login(email.trim(), password);
      navigate(u.diagnostic_completed || u.role === 'teacher' ? '/app' : '/onboarding');
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setPending(false);
    }
  };

  return (
    <AuthLayout
      title={t('auth.login_title')}
      subtitle={t('auth.login_sub')}
      footer={
        <>
          {t('auth.no_account')}{' '}
          <Link to="/register" className="font-semibold text-brand-700 hover:underline">
            {t('nav.register')}
          </Link>
        </>
      }
    >
      <form onSubmit={submit} className="space-y-4" noValidate>
        <Field label={t('auth.email')}>
          <Input type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </Field>
        <Field label={t('auth.password')}>
          <Input type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
        </Field>
        {error && <ErrorState message={error} />}
        <Button type="submit" size="lg" className="w-full" loading={pending}>
          {t('auth.submit_login')}
        </Button>
      </form>
    </AuthLayout>
  );
}

export function Register() {
  const { t, locale } = useI18n();
  const { register } = useAuth();
  const navigate = useNavigate();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [displayName, setDisplayName] = useState('');
  const [role, setRole] = useState<Role>('learner');
  const [language, setLanguage] = useState<Language>(locale);
  const [pending, setPending] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const submit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (password.length < 8) {
      setError(t('auth.password_hint'));
      return;
    }
    setPending(true);
    setError(null);
    try {
      await register({ email: email.trim(), password, display_name: displayName.trim(), preferred_language: language, role });
      navigate(role === 'teacher' ? '/app' : '/onboarding');
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setPending(false);
    }
  };

  return (
    <AuthLayout
      title={t('auth.register_title')}
      subtitle={t('auth.register_sub')}
      footer={
        <>
          {t('auth.have_account')}{' '}
          <Link to="/login" className="font-semibold text-brand-700 hover:underline">
            {t('nav.login')}
          </Link>
        </>
      }
    >
      <form onSubmit={submit} className="space-y-4" noValidate>
        <fieldset>
          <legend className="mb-2 block text-sm font-medium text-ink">{t('auth.role')}</legend>
          <div className="grid grid-cols-2 gap-2">
            {(
              [
                { value: 'learner', icon: <LuUserRound className="h-5 w-5" />, label: t('auth.role_learner'), desc: t('auth.role_learner_desc') },
                { value: 'teacher', icon: <LuGraduationCap className="h-5 w-5" />, label: t('auth.role_teacher'), desc: t('auth.role_teacher_desc') },
              ] as const
            ).map((r) => (
              <button
                key={r.value}
                type="button"
                onClick={() => setRole(r.value)}
                aria-pressed={role === r.value}
                className={cn(
                  'flex flex-col items-start gap-1 rounded-2xl border p-3 text-start transition-colors',
                  role === r.value ? 'border-brand-600 bg-brand-50 text-ink' : 'border-line bg-white text-ink-soft hover:border-brand-300',
                )}
              >
                <span className={cn(role === r.value ? 'text-brand-700' : 'text-ink-muted')}>{r.icon}</span>
                <span className="text-sm font-semibold text-ink">{r.label}</span>
                <span className="text-xs text-ink-muted">{r.desc}</span>
              </button>
            ))}
          </div>
        </fieldset>
        <Field label={t('auth.display_name')} hint={t('auth.display_name_hint')}>
          <Input autoComplete="nickname" required minLength={2} maxLength={40} value={displayName} onChange={(e) => setDisplayName(e.target.value)} />
        </Field>
        <Field label={t('auth.email')}>
          <Input type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </Field>
        <Field label={t('auth.password')} hint={t('auth.password_hint')}>
          <Input type="password" autoComplete="new-password" required minLength={8} value={password} onChange={(e) => setPassword(e.target.value)} />
        </Field>
        <Field label={t('auth.preferred_language')}>
          <Select value={language} onChange={(e) => setLanguage(e.target.value as Language)}>
            {LANGUAGES.map((l) => (
              <option key={l} value={l}>
                {t(`lang.${l}`)}
              </option>
            ))}
          </Select>
        </Field>
        {error && <ErrorState message={error} />}
        <Button type="submit" size="lg" className="w-full" loading={pending}>
          {t('auth.submit_register')}
        </Button>
      </form>
    </AuthLayout>
  );
}
