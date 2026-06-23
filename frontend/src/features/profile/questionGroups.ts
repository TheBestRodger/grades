import type { ProfileQuestion } from "../../types";
import type { ProfileSection } from "./types";

export function groupQuestionsBySection(questions: ProfileQuestion[]): ProfileSection[] {
  const sections: ProfileSection[] = [];
  const lookup = new Map<string, ProfileSection>();

  questions.forEach((question) => {
    let section = lookup.get(question.section);
    if (!section) {
      section = { title: question.section, questions: [] };
      lookup.set(question.section, section);
      sections.push(section);
    }
    section.questions.push(question);
  });

  return sections;
}
