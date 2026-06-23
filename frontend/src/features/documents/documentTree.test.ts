import { describe, expect, it } from "vitest";

import type { OrgNode } from "../../types";
import { filterTree, positionCount, visibleTree } from "./documentTree";

const nodes: OrgNode[] = [
  {
    id: 1,
    name: "Администрация",
    department_code: null,
    is_demo: false,
    positions: [
      {
        id: 10,
        title: "Бухгалтер",
        position_code: null,
        approved_fte: null,
        assigned_fte: null,
        vacancy_fte: null,
        assignments: [],
      },
    ],
    children: [
      {
        id: 2,
        name: "ИТ отдел",
        department_code: null,
        is_demo: false,
        positions: [
          {
            id: 20,
            title: "Системный администратор",
            position_code: null,
            approved_fte: null,
            assigned_fte: null,
            vacancy_fte: null,
            assignments: [],
          },
        ],
        children: [],
      },
    ],
  },
];

describe("documentTree", () => {
  it("counts positions recursively", () => {
    expect(positionCount(nodes[0])).toBe(2);
  });

  it("returns visible tree for empty filter", () => {
    const visible = visibleTree(nodes);

    expect(visible[0].source.name).toBe("Администрация");
    expect(visible[0].children[0].source.name).toBe("ИТ отдел");
  });

  it("filters units and expands matching branches", () => {
    const result = filterTree(nodes, "ит");

    expect(result.nodes[0].children[0].source.name).toBe("ИТ отдел");
    expect(result.expanded.has(1)).toBe(true);
    expect(result.expanded.has(2)).toBe(true);
  });

  it("filters positions and returns empty list when nothing matches", () => {
    expect(filterTree(nodes, "бухгалтер").nodes[0].positions[0].title).toBe("Бухгалтер");
    expect(filterTree(nodes, "юрист").nodes).toEqual([]);
  });
});
