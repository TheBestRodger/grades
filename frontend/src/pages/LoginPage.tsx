import { type FormEvent, useState } from "react";

export function LoginPage({
  authError,
  authMessage,
  isRequesting,
  onLogin,
}: {
  authError: string | null;
  authMessage: string | null;
  isRequesting: boolean;
  onLogin: (username: string, password: string) => void;
}) {
  const [username, setUsername] = useState("");
  const [password, setPassword] = useState("");

  function submit(event: FormEvent) {
    event.preventDefault();
    onLogin(username, password);
  }

  return (
    <main className="flex min-h-screen items-center justify-center bg-slate-50 px-6 py-10 text-slate-800">
      <section className="w-full max-w-5xl overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm">
        <div className="grid lg:grid-cols-[1fr_420px]">
          <div className="p-8 lg:p-10">
            <div className="flex items-center gap-4">
              <div className="rounded-xl bg-blue-950 px-3 py-2 font-bold text-white">МГТУ</div>
              <div>
                <p className="text-xs font-semibold uppercase tracking-[0.2em] text-blue-700">
                  Профилирование должностей
                </p>
                <h1 className="text-2xl font-bold text-slate-950">Вход в систему</h1>
              </div>
            </div>

            <div className="mt-8 max-w-xl">
              <p className="text-sm text-slate-600">
                Введите email и временный пароль, выданные HR. После входа откроется личный кабинет
                сотрудника, руководителя или HR.
              </p>
              {(authMessage || authError) && (
                <div className="mt-5 rounded-2xl border border-blue-100 bg-blue-50 px-4 py-3 text-sm">
                  {authMessage && <p className="text-blue-950">{authMessage}</p>}
                  {authError && <p className="mt-1 text-red-700">{authError}</p>}
                </div>
              )}
            </div>
          </div>

          <aside className="border-t border-slate-100 bg-slate-50 p-8 lg:border-l lg:border-t-0 lg:p-10">
            <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">
              Авторизация
            </p>
            <h2 className="mt-2 text-xl font-bold text-slate-950">Вход по email и паролю</h2>
            <form className="mt-5 space-y-4" onSubmit={submit}>
              <label className="block text-sm font-medium text-slate-700">
                Email
                <input
                  autoComplete="username"
                  className="mt-2 block w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none focus:border-blue-700"
                  onChange={(event) => setUsername(event.target.value)}
                  placeholder="name@example.ru"
                  required
                  value={username}
                />
              </label>
              <label className="block text-sm font-medium text-slate-700">
                Пароль
                <input
                  autoComplete="current-password"
                  className="mt-2 block w-full rounded-xl border border-slate-200 bg-white px-4 py-3 text-sm outline-none focus:border-blue-700"
                  onChange={(event) => setPassword(event.target.value)}
                  placeholder="пароль"
                  required
                  type="password"
                  value={password}
                />
              </label>
              <button
                className="w-full rounded-xl bg-blue-950 px-4 py-3 text-sm font-semibold text-white disabled:opacity-50"
                disabled={isRequesting}
                type="submit"
              >
                {isRequesting ? "Вхожу..." : "Войти"}
              </button>
            </form>
          </aside>
        </div>
      </section>
    </main>
  );
}
