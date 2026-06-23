export function WorkContourPlaceholder() {
  return (
    <section className="rounded-3xl border border-dashed border-slate-300 bg-white p-6 shadow-sm">
      <p className="text-xs font-semibold uppercase tracking-[0.18em] text-slate-400">
        Рабочий контур
      </p>
      <h2 className="mt-2 text-xl font-bold text-slate-950">Данные пока не загружены</h2>
      <p className="mt-2 max-w-3xl text-sm text-slate-600">
        Структура и документальное покрытие рабочего ШР уже доступны в соответствующих вкладках.
        Для кампаний, проверок и профилей нужен следующий слой: добавление сотрудников, руководителей
        и ручное сопоставление документов.
      </p>
      <div className="mt-5 rounded-2xl bg-slate-50 p-4 text-sm text-slate-600">
        <p className="font-semibold text-slate-900">Будущая схема</p>
        <p className="mt-2">Организация → подразделения → штатные строки → назначения сотрудников → кампании.</p>
      </div>
    </section>
  );
}
