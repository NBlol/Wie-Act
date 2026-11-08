# Business-model note — EdNova AI

*Target users · value proposition · adoption path · sustainability beyond the hackathon.*

## 1. The problem we monetise

Peer learning is effective but unstructured: one learner dominates, others stay silent, simple questions
go unasked, wrong explanations go unchallenged, and a single explanation style fails most of the group.
Institutions already pay for tutoring hours, LMS licences and remedial sessions; EdNova makes every
existing study session more productive at a fraction of the cost of human tutoring.

## 2. Target users

| Segment | Who | Pain | How EdNova fits |
|---|---|---|---|
| **Universities & engineering schools** (first wedge: Tunisian public and private higher education, IEEE student branches) | 1st–3rd-year students, TAs, department heads | large cohorts, few TAs, high failure rates in foundation courses, French/Arabic/Darija mix | study rooms per course, teacher dashboard, document-grounded tutoring on the official course PDFs |
| **Training centres & bootcamps** (vocational, professional reskilling) | trainers, cohorts of 15–40 | heterogeneous levels, limited trainer time | diagnostic → personalised path, quizzes from the centre's material, analytics for trainers |
| **Self-learning communities** (exam prep groups, online communities, NGOs) | motivated learners without a tutor | isolation, no feedback, no structure | AI moderator + roadmaps + gamified progress |
| **Secondary schools** (later) | teachers, pupils preparing the baccalauréat | revision load, language barriers | revision notes, Darija explanations, parent-safe privacy model |

## 3. Value proposition

* **For learners** — a companion that explains the way *you* learn, in *your* language, hints before
  answering, keeps the group balanced and tells you what to do next. Measurable: mastery per skill,
  streaks, badges.
* **For teachers / trainers** — fewer repetitive questions, early visibility of confusion hotspots and weak
  skills, quizzes and notes generated from their own material, no extra grading.
* **For institutions** — higher pass rates and engagement at a predictable cost; privacy-by-design
  (pseudonyms, data erasure, aggregates only); runs on-premise or in the cloud; low inference cost thanks to
  compact-first routing, caching and local retrieval.

## 4. Adoption path

1. **Hackathon → pilot (0–3 months)**: deploy with one department of ENICarthage / a partner school,
   2–3 courses, ~100 students, using the challenge platform or an equivalent OpenAI-compatible service.
   Success metrics: weekly active learners, participation-balance score in rooms, quiz mastery gain,
   teacher satisfaction.
2. **Campus licence (3–9 months)**: integrate with the institution's SSO and LMS (LTI/SCORM export of
   quizzes and notes), add the teacher dashboard to course pages, run train-the-trainer sessions
   (IEEE student branches as ambassadors).
3. **Training centres & B2B2C (9–18 months)**: white-label rooms for bootcamps and corporate academies;
   content partners (publishers) supply pre-indexed material.
4. **Regional expansion**: Maghreb/francophone Africa, where the French-Arabic-dialect mix and the
   scarcity of tutors make the multilingual companion a differentiator.

## 5. Revenue model

| Stream | Price point (indicative) | Notes |
|---|---|---|
| Institution licence | per active learner per year (tiered by cohort size) | includes teacher dashboard, SSO, on-prem option |
| Training-centre subscription | per cohort per month | content indexing + analytics |
| Freemium for self-learners | free tier with quotas on large-model calls; low-cost premium | the router's compact-first design keeps the free tier affordable |
| Services | onboarding, content indexing, custom integrations | delivered with student-branch partners |

## 6. Unit economics driven by the architecture

* A tutor turn costs ≤ 2 model calls, most of them on the compact category; MCQs cost 0; equivalent
  requests are cached; retrieval is local. Target: **< 30 % of calls on the large category** (visible in
  the AI-efficiency panel).
* Infrastructure: one PostgreSQL instance + stateless API containers; no GPU required on our side.
* Costs scale with *answers that needed the large model*, which the routing table minimises.

## 7. Sustainability beyond the hackathon

* **Technical**: provider-agnostic adapters (OpenAI-compatible / Anthropic), documented routing table,
  tests with a fake provider so the project survives platform changes; Docker deployment.
* **Organisational**: maintained by the team with IEEE student-branch contributors; open contribution
  guidelines; institution pilots fund the first year.
* **Partnerships**: universities (pilot sites), IEEE WIE/ENICarthage (community and testing),
  content publishers (material), regional ed-tech accelerators.
* **Risks & mitigations**: inference cost spikes → quotas + compact-first + cache; model quality drift →
  evaluation set of 50 questions per language re-run on every release; privacy regulation → data
  minimisation, erasure, on-prem option; adoption friction → teacher dashboard and zero-grading quizzes
  deliver value to the people who decide.

## 8. Twelve-month milestones

| Quarter | Milestone |
|---|---|
| Q1 | Pilot with 100 students; real-user testing report; Darija evaluation set |
| Q2 | SSO + LMS export; teacher dashboard v2; first paid campus licence |
| Q3 | Training-centre offer; content partner; voice interaction prototype |
| Q4 | 3 institutions, 2 000 learners; regional partner in the Maghreb |
