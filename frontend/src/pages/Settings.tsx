import React, { useEffect, useState } from 'react';
import { LuShieldCheck, LuTrash2, LuRotateCcw, LuSchool, LuCheck } from 'react-icons/lu';
import { useNavigate } from '../lib/router';
import { useI18n } from '../lib/i18n';
import { useAuth } from '../lib/auth';
import { api, errorMessage, LANGUAGES, LEARNING_STYLES, LEVELS, type Language, type LearningStyle, type Level } from '../lib/api';
import { useToast } from '../lib/toast';
import { Button, Card, CardTitle, ErrorState, Field, Input, Modal, PageHeader, Select } from '../components/ui';
import type { TranslationKey } from '../i18n/en';

export function Settings() {
  const { t, setLocale } = useI18n();
  const { user, setUser, logout } = useAuth();
  const navigate = useNavigate();
  const toast = useToast();
  const [displayName, setDisplayName] = useState(user?.display_name ?? '');
  const [language, setLanguage] = useState<Language>(user?.preferred_language ?? 'en');
  const [script, setScript] = useState<'arabic' | 'latin'>(user?.darija_script ?? 'arabic');
  const [style, setStyle] = useState<LearningStyle | ''>(user?.learning_style ?? '');
  const [level, setLevel] = useState<Level | ''>(user?.level ?? '');
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [classCode, setClassCode] = useState('');
  const [joining, setJoining] = useState(false);
  const [joinMsg, setJoinMsg] = useState<string | null>(null);
  const [deleteOpen, setDeleteOpen] = useState(false);
  const [confirmText, setConfirmText] = useState('');
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    if (!user) return;
    setDisplayName(user.display_name);
    setLanguage(user.preferred_language);
    setScript(user.darija_script);
    setStyle(user.learning_style ?? '');
    setLevel(user.level ?? '');
  }, [user]);

  const save = async (e: React.FormEvent) => {
    e.preventDefault();
    setSaving(true);
    setError(null);
    try {
      const updated = await api.updateMe({
        display_name: displayName.trim(),
        preferred_language: language,
        darija_script: script,
        learning_style: style || null,
        level: level || null,
      });
      setUser(updated);
      setLocale(updated.preferred_language);
      toast('success', t('set.saved'));
    } catch (err) {
      setError(errorMessage(err));
    } finally {
      setSaving(false);
    }
  };

  const joinClass = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!classCode.trim()) return;
    setJoining(true);
    setJoinMsg(null);
    try {
      await api.joinClass(classCode.trim().toUpperCase());
      setJoinMsg(t('set.class_joined'));
      setClassCode('');
    } catch (err) {
      setJoinMsg(errorMessage(err));
    } finally {
      setJoining(false);
    }
  };

  const remove = async () => {
    setDeleting(true);
    try {
      await api.deleteMe();
      logout();
      navigate('/');
    } catch (err) {
      setError(errorMessage(err));
      setDeleting(false);
    }
  };

  return (
    <div className="space-y-6">
      <PageHeader title={t('set.title')} />
      <div className="grid gap-4 lg:grid-cols-[1fr_340px]">
        <div className="space-y-4">
          <Card elevated>
            <CardTitle>{t('set.profile')}</CardTitle>
            <form onSubmit={save} className="space-y-4">
              <Field label={t('set.display_name')} hint={t('auth.display_name_hint')}>
                <Input value={displayName} onChange={(e) => setDisplayName(e.target.value)} minLength={2} maxLength={40} required />
              </Field>
              <div className="grid gap-4 sm:grid-cols-2">
                <Field label={t('set.language')}>
                  <Select value={language} onChange={(e) => setLanguage(e.target.value as Language)}>
                    {LANGUAGES.map((l) => (
                      <option key={l} value={l}>
                        {t(`lang.${l}` as TranslationKey)}
                      </option>
                    ))}
                  </Select>
                </Field>
                {language === 'tn' && (
                  <Field label={t('set.darija_script')}>
                    <Select value={script} onChange={(e) => setScript(e.target.value as 'arabic' | 'latin')}>
                      <option value="arabic">{t('set.script_arabic')}</option>
                      <option value="latin">{t('set.script_latin')}</option>
                    </Select>
                  </Field>
                )}
                <Field label={t('set.learning_style')}>
                  <Select value={style} onChange={(e) => setStyle(e.target.value as LearningStyle | '')}>
                    <option value="">{t('set.not_set')}</option>
                    {LEARNING_STYLES.map((s) => (
                      <option key={s} value={s}>
                        {t(`style.${s}` as TranslationKey)}
                      </option>
                    ))}
                  </Select>
                </Field>
                <Field label={t('set.level')}>
                  <Select value={level} onChange={(e) => setLevel(e.target.value as Level | '')}>
                    <option value="">{t('set.not_set')}</option>
                    {LEVELS.map((l) => (
                      <option key={l} value={l}>
                        {t(`level.${l}` as TranslationKey)}
                      </option>
                    ))}
                  </Select>
                </Field>
              </div>
              {error && <ErrorState message={error} />}
              <div className="flex flex-wrap gap-2">
                <Button type="submit" loading={saving}>
                  {t('common.save')}
                </Button>
                <Button variant="secondary" icon={<LuRotateCcw className="h-4 w-4" />} onClick={() => navigate('/onboarding')}>
                  {t('set.retake')}
                </Button>
              </div>
            </form>
          </Card>

          {user?.role === 'learner' && (
            <Card>
              <CardTitle>
                <span className="flex items-center gap-2">
                  <LuSchool className="h-4 w-4 text-brand-600" aria-hidden />
                  {t('set.class_title')}
                </span>
              </CardTitle>
              <p className="mb-3 text-sm text-ink-soft">{t('set.class_desc')}</p>
              <form onSubmit={joinClass} className="flex flex-col gap-2 sm:flex-row sm:items-end">
                <Field label={t('set.class_code')} className="flex-1">
                  <Input value={classCode} onChange={(e) => setClassCode(e.target.value)} className="uppercase tracking-widest" maxLength={8} />
                </Field>
                <Button type="submit" variant="secondary" loading={joining} disabled={!classCode.trim()}>
                  {t('common.join')}
                </Button>
              </form>
              {joinMsg && (
                <p className="mt-2 flex items-center gap-1.5 text-sm text-ink-soft">
                  <LuCheck className="h-4 w-4 text-mint-600" aria-hidden />
                  {joinMsg}
                </p>
              )}
            </Card>
          )}
        </div>

        <div className="space-y-4">
          <Card>
            <CardTitle>
              <span className="flex items-center gap-2">
                <LuShieldCheck className="h-4 w-4 text-mint-600" aria-hidden />
                {t('set.privacy_title')}
              </span>
            </CardTitle>
            <ul className="space-y-2 text-sm text-ink-soft">
              <li>{t('set.privacy_p1')}</li>
              <li>{t('set.privacy_p2')}</li>
              <li>{t('set.privacy_p3')}</li>
            </ul>
          </Card>
          <Card className="border-rose-500/20">
            <CardTitle>
              <span className="text-rose-600">{t('set.danger')}</span>
            </CardTitle>
            <p className="mb-3 text-sm text-ink-soft">{t('set.delete_desc')}</p>
            <Button variant="danger" icon={<LuTrash2 className="h-4 w-4" />} onClick={() => setDeleteOpen(true)}>
              {t('set.danger')}
            </Button>
          </Card>
        </div>
      </div>

      <Modal
        open={deleteOpen}
        onClose={() => setDeleteOpen(false)}
        title={t('set.danger')}
        footer={
          <>
            <Button variant="ghost" onClick={() => setDeleteOpen(false)}>
              {t('common.cancel')}
            </Button>
            <Button variant="danger" disabled={confirmText !== 'DELETE'} loading={deleting} onClick={() => void remove()}>
              {t('common.delete')}
            </Button>
          </>
        }
      >
        <p className="text-sm text-ink-soft">{t('set.delete_desc')}</p>
        <Field label={t('set.delete_confirm')} className="mt-4">
          <Input value={confirmText} onChange={(e) => setConfirmText(e.target.value)} autoComplete="off" />
        </Field>
      </Modal>
    </div>
  );
}

export default Settings;
