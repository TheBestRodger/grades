import { type FormEvent, useEffect, useState } from "react";

import { downloadCredentialsExport } from "../../api";

import type { Assignment, EmployeeAssignmentUpdate, EmployeePasswordResetResult } from "../../types";

interface EmployeeEditModalProps {
  assignment: Assignment | null;
  isSaving: boolean;
  error: string | null;
  isResettingPassword: boolean;
  passwordResetError: string | null;
  passwordResetResult: EmployeePasswordResetResult | null;
  onClose: () => void;
  onSave: (payload: EmployeeAssignmentUpdate) => void;
  onResetPassword: () => Promise<EmployeePasswordResetResult>;
}

export function EmployeeEditModal({
  assignment,
  isSaving,
  error,
  isResettingPassword,
  passwordResetError,
  passwordResetResult,
  onClose,
  onSave,
  onResetPassword,
}: EmployeeEditModalProps) {
  const [fullName, setFullName] = useState("");
  const [email, setEmail] = useState("");
  const [systemRole, setSystemRole] = useState<"employee" | "manager">("employee");
  const [isHr, setIsHr] = useState(false);
  const [copyMessage, setCopyMessage] = useState<string | null>(null);
  const [showPasswordResetConfirm, setShowPasswordResetConfirm] = useState(false);

  useEffect(() => {
    setFullName(assignment?.employee_name ?? "");
    setEmail(assignment?.employee_email ?? "");
    setSystemRole(assignment?.role === "manager" ? "manager" : "employee");
    setIsHr(Boolean(assignment?.is_hr));
    setCopyMessage(null);
    setShowPasswordResetConfirm(false);
  }, [assignment]);

  if (!assignment) return null;

  function submit(event: FormEvent) {
    event.preventDefault();
    onSave({
      full_name: fullName,
      email,
      system_role: systemRole,
      is_hr: isHr,
    });
  }

  const canSave = fullName.trim().length >= 3 && email.trim().includes("@");

  async function confirmPasswordReset() {
    setCopyMessage(null);
    setShowPasswordResetConfirm(false);
    await onResetPassword();
  }

  async function copyPassword() {
    if (!passwordResetResult?.password) return;
    if (navigator.clipboard?.writeText) {
      await navigator.clipboard.writeText(passwordResetResult.password);
    } else {
      const textarea = document.createElement("textarea");
      textarea.value = passwordResetResult.password;
      textarea.style.position = "fixed";
      textarea.style.opacity = "0";
      document.body.appendChild(textarea);
      textarea.focus();
      textarea.select();
      document.execCommand("copy");
      textarea.remove();
    }
    setCopyMessage("Пароль скопирован.");
  }

  async function downloadPasswordFile() {
    const currentAssignment = assignment;
    if (!passwordResetResult || !currentAssignment) return;
    await downloadCredentialsExport([
      {
        full_name: passwordResetResult.full_name,
        email: passwordResetResult.email,
        username: passwordResetResult.username ?? "",
        password: passwordResetResult.password,
        role: currentAssignment.is_hr
          ? "HR"
          : currentAssignment.role === "manager"
            ? "Руководитель"
            : "Сотрудник",
        position: passwordResetResult.staffing_title,
      },
    ]);
  }

  return (
    <div className="fixed inset-0 z-20 grid place-items-center bg-slate-950/40 px-4">
      <form
        className="w-full max-w-2xl rounded-3xl bg-white p-6 shadow-2xl"
        onSubmit={submit}
      >
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-blue-700">
              HR: карточка сотрудника
            </p>
            <h3 className="mt-1 text-xl font-bold text-slate-950">Редактирование данных</h3>
          </div>
          <button className="rounded-xl px-3 py-2 text-slate-500 hover:bg-slate-100" onClick={onClose} type="button">
            Закрыть
          </button>
        </div>

        <div className="mt-6 grid gap-4">
          <label className="text-sm font-medium text-slate-700">
            ФИО
            <input
              className="mt-2 block w-full rounded-xl border border-slate-200 bg-white px-3 py-2 outline-none focus:border-blue-700"
              onChange={(event) => setFullName(event.target.value)}
              required
              value={fullName}
            />
          </label>
          <label className="text-sm font-medium text-slate-700">
            Email
            <input
              className="mt-2 block w-full rounded-xl border border-slate-200 bg-white px-3 py-2 outline-none focus:border-blue-700"
              onChange={(event) => setEmail(event.target.value)}
              required
              type="email"
              value={email}
            />
          </label>
          <label className="text-sm font-medium text-slate-700">
            Основная роль
            <select
              className="mt-2 block w-full rounded-xl border border-slate-200 bg-white px-3 py-2 outline-none focus:border-blue-700"
              onChange={(event) => setSystemRole(event.target.value as "employee" | "manager")}
              value={systemRole}
            >
              <option value="employee">Сотрудник</option>
              <option value="manager">Руководитель</option>
            </select>
          </label>
          <label className="flex items-center gap-3 rounded-xl border border-blue-100 bg-blue-50 px-4 py-3 text-sm font-semibold text-blue-950">
            <input
              checked={isHr}
              className="h-4 w-4 accent-blue-900"
              onChange={(event) => setIsHr(event.target.checked)}
              type="checkbox"
            />
            Дать права HR
          </label>
        </div>

        <div className="mt-5 rounded-2xl border border-amber-200 bg-amber-50 px-4 py-4">
          <div className="flex flex-wrap items-start justify-between gap-4">
            <div>
              <p className="text-sm font-semibold text-slate-900">Сбросить пароль</p>
              <p className="mt-1 text-sm text-slate-600">
                HR может перевыпустить пароль, если сотрудник не успел войти или его потерял.
              </p>
            </div>
            <button
              className="rounded-xl bg-amber-600 px-4 py-2 text-sm font-semibold text-white hover:bg-amber-700 disabled:opacity-50"
              disabled={isResettingPassword}
              onClick={() => setShowPasswordResetConfirm(true)}
              type="button"
            >
              {isResettingPassword ? "Перевыпускаю..." : "Перевыпустить пароль"}
            </button>
          </div>

          {showPasswordResetConfirm && (
            <div className="mt-4 rounded-xl border border-amber-300 bg-white px-4 py-4 shadow-sm">
              <p className="text-sm font-semibold text-slate-950">Перевыпустить пароль?</p>
              <p className="mt-1 text-sm text-slate-600">
                Старый пароль перестанет работать. Новый пароль будет показан один раз.
              </p>
              <div className="mt-4 flex flex-wrap justify-end gap-2">
                <button
                  className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
                  onClick={() => setShowPasswordResetConfirm(false)}
                  type="button"
                >
                  Отмена
                </button>
                <button
                  className="rounded-lg bg-amber-600 px-3 py-2 text-sm font-semibold text-white hover:bg-amber-700 disabled:opacity-50"
                  disabled={isResettingPassword}
                  onClick={confirmPasswordReset}
                  type="button"
                >
                  Да, перевыпустить
                </button>
              </div>
            </div>
          )}

          {passwordResetResult && (
            <div className="mt-4 rounded-xl bg-white px-4 py-4 shadow-sm">
              <p className="text-xs font-semibold uppercase tracking-[0.16em] text-amber-700">
                Новый пароль показан один раз
              </p>
              <p className="mt-3 text-sm text-slate-700">
                Email для входа: <span className="font-semibold text-slate-950">{passwordResetResult.username}</span>
              </p>
              <div className="mt-3 flex flex-wrap items-center gap-3">
                <code className="rounded-lg bg-slate-100 px-3 py-2 text-sm font-semibold text-slate-900">
                  {passwordResetResult.password}
                </code>
                <button
                  className="rounded-lg border border-slate-200 px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-50"
                  onClick={copyPassword}
                  type="button"
                >
                  Скопировать
                </button>
                <button
                  className="rounded-lg border border-blue-200 px-3 py-2 text-sm font-medium text-blue-900 hover:bg-blue-50"
                  onClick={downloadPasswordFile}
                  type="button"
                >
                  Скачать XLSX
                </button>
              </div>
              {copyMessage && <p className="mt-2 text-sm text-emerald-700">{copyMessage}</p>}
            </div>
          )}

          {passwordResetError && <p className="mt-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{passwordResetError}</p>}
        </div>

        {error && <p className="mt-4 rounded-xl bg-red-50 px-4 py-3 text-sm text-red-700">{error}</p>}
        <div className="mt-6 flex justify-end gap-3">
          <button className="rounded-xl border border-slate-200 px-5 py-2.5 text-sm font-medium" onClick={onClose} type="button">
            Отмена
          </button>
          <button
            className="rounded-xl bg-blue-900 px-5 py-2.5 text-sm font-semibold text-white disabled:opacity-50"
            disabled={isSaving || !canSave}
            type="submit"
          >
            {isSaving ? "Сохраняю..." : "Сохранить"}
          </button>
        </div>
      </form>
    </div>
  );
}
