import { pruneAnswers, requirementsFrom, visibleQuestions, type Answers } from '@/components/projects/questionnaire';

const ids = (answers: Answers) => new Set(visibleQuestions(answers).map(question => question.id));

describe('questionnaire branches and answer preparation', () => {
  it.each([
    ['Web Application', ['webKind', 'frontend', 'backend'], ['platform', 'problem', 'language']],
    ['Mobile Application', ['platform', 'mobileApproach', 'frontend', 'backend'], ['webKind', 'problem']],
    ['AI / Machine Learning', ['problem', 'model', 'dataset', 'language'], ['webKind', 'platform', 'frontend']],
    ['Desktop Application', ['language', 'backend'], ['webKind', 'platform', 'frontend']],
    ['API / Backend Service', ['language'], ['webKind', 'platform', 'frontend', 'backend']],
    ['Data Analytics', ['problem', 'dataset', 'language'], ['webKind', 'platform', 'frontend']],
    ['Other', ['deployment'], ['webKind', 'platform', 'frontend']],
  ])('uses the existing %s project path', (category, present, absent) => {
    const visible = ids({ category });
    present.forEach(id => expect(visible.has(id)).toBe(true));
    absent.forEach(id => expect(visible.has(id)).toBe(false));
  });

  it('prunes nested and sibling answers until no hidden parent can keep them alive', () => {
    const oldPath: Answers = {
      category: 'Web Application', backend: 'Yes', auth: 'Yes',
      authMethods: ['Other'], authOther: 'Passkey',
      database: 'Yes', databaseDetails: 'PostgreSQL configured',
    };
    const next = pruneAnswers({ ...oldPath, category: 'AI / Machine Learning' });
    expect(next).toEqual({ category: 'AI / Machine Learning' });
    expect(requirementsFrom(next, 'AI project').answers).toEqual({ category: 'AI / Machine Learning' });
  });

  it('shows AI model and dataset details only after their Yes answers', () => {
    const visible = ids({ category: 'AI / Machine Learning', model: 'Yes', dataset: 'Yes' });
    expect(visible.has('modelDetails')).toBe(true);
    expect(visible.has('datasetDetails')).toBe(true);
    expect(ids({ category: 'AI / Machine Learning', model: 'No', dataset: 'No' }).has('modelDetails')).toBe(false);
    expect(ids({ category: 'AI / Machine Learning', model: 'No', dataset: 'No' }).has('datasetDetails')).toBe(false);
  });

  it('preserves configured custom follow-up text and multi-select choices in review data', () => {
    const answers: Answers = {
      category: 'Mobile Application', platform: ['Android', 'iOS'],
      mobileApproach: 'Other',
    };
    const prepared = requirementsFrom(answers, 'Mobile client', { mobileApproach: ' Kotlin Multiplatform ' });
    expect(prepared.answers).toMatchObject(answers);
    expect(prepared.customAnswers).toEqual({ mobileApproach: 'Kotlin Multiplatform' });
    expect(prepared.sections.flatMap(section => section.items)).toEqual(expect.arrayContaining([
      expect.objectContaining({ id: 'platform', answer: ['Android', 'iOS'] }),
      expect.objectContaining({ id: 'mobileApproach:other', answer: 'Kotlin Multiplatform' }),
    ]));
  });

  it('treats blank and whitespace-only strings as unanswered', () => {
    expect(requirementsFrom({ category: 'AI / Machine Learning', problem: '   ' }, 'AI').answers).toEqual({ category: 'AI / Machine Learning' });
    expect(requirementsFrom({ category: 'AI / Machine Learning', problem: '  Classify support requests  ' }, 'AI').answers.problem).toBe('Classify support requests');
  });
});
