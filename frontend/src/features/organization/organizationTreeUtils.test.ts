import { describe, expect, it } from "vitest";

import type { Campaign, OrgNode } from "../../types";
import { assignmentIds, displayFte, filterTree, positionCount, selectionState, unitIds, visibleTree } from "./organizationTreeUtils";

const tree: OrgNode[] = [
  {
    id: 1,
    name: "Главный офис",
    department_code: "HQ",
    is_demo: false,
    positions: [
      {
        id: 10,
        title: "Инженер",
        position_code: "ENG",
        approved_fte: 1,
        assigned_fte: 1,
        vacancy_fte: 0,
        assignments: [
          {
            id: 100,
            employee_id: 1000,
            employee_name: "Иван Иванов",
            employee_email: "ivan@example.com",
            fte: 1,
            role: "employee",
            is_hr: false,
          },
        ],
      },
    ],
    children: [
      {
        id: 2,
        name: "Разработка",
        department_code: "DEV",
        is_demo: false,
        positions: [
          {
            id: 20,
            title: "Frontend разработчик",
            position_code: "FE",
            approved_fte: 2,
            assigned_fte: 1,
            vacancy_fte: 1,
            assignments: [
              {
                id: 200,
                employee_id: 2000,
                employee_name: "Пётр Петров",
                employee_email: "petr@example.com",
                fte: 1,
                role: "manager",
                is_hr: false,
              },
            ],
          },
        ],
        children: [],
      },
    ],
  },
];

function campaign(overrides: Partial<Campaign> = {}): Campaign {
  return {
    id: 1,
    scope: "demo",
    is_demo: true,
    name: "Кампания",
    status: "draft",
    due_at: null,
    participants_expected: 0,
    total_participants_expected: 0,
    active_wave_id: null,
    active_wave_name: null,
    waves: [],
    participant_assignment_ids: [],
    selected_org_unit_ids: [],
    selected_units_count: 0,
    selected_staffing_lines: 0,
    selected_approved_fte: 0,
    status_counts: {},
    created_at: null,
    ...overrides,
  };
}

describe("organizationTreeUtils", () => {
  it("formats FTE values", () => {
    expect(displayFte(null)).toBe("-");
    expect(displayFte(1.234)).toBe("1,23");
  });

  it("collects assignment and unit ids recursively", () => {
    expect(assignmentIds(tree[0])).toEqual([100, 200]);
    expect(unitIds(tree[0])).toEqual([1, 2]);
  });

  it("counts positions recursively", () => {
    expect(positionCount(tree[0])).toBe(2);
  });

  it("returns visible tree without filtering", () => {
    const visible = visibleTree(tree);

    expect(visible[0].source.name).toBe("Главный офис");
    expect(visible[0].children[0].source.name).toBe("Разработка");
  });

  it("filters by unit, position and assignment names", () => {
    const byPosition = filterTree(tree, "frontend");
    expect(byPosition.matchCount).toBe(1);
    expect(byPosition.expandedUnitIds.has(1)).toBe(true);
    expect(byPosition.expandedUnitIds.has(2)).toBe(true);

    const byEmployee = filterTree(tree, "иван");
    expect(byEmployee.nodes[0].positions[0].assignments[0].employee_name).toBe("Иван Иванов");

    const noMatch = filterTree(tree, "нет совпадений");
    expect(noMatch.nodes).toEqual([]);
    expect(noMatch.matchCount).toBe(0);
  });

  it("calculates selection state for demo and work campaigns", () => {
    expect(selectionState(tree[0], null)).toMatchObject({ selected: 0, total: 0 });
    expect(selectionState(tree[0], campaign({ participant_assignment_ids: [] }))).toMatchObject({ selected: 0, total: 2 });
    expect(selectionState(tree[0], campaign({ participant_assignment_ids: [100] }))).toMatchObject({ selected: 1, total: 2 });
    expect(selectionState(tree[0], campaign({ participant_assignment_ids: [100, 200] }))).toMatchObject({ selected: 2, total: 2 });
    expect(selectionState(tree[0], campaign({ scope: "work", selected_org_unit_ids: [1, 2] }))).toMatchObject({
      selected: 2,
      total: 2,
    });
  });
});
