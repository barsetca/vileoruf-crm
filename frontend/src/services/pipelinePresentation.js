const stageKeys = {
  "New Lead": "newLead",
  Contact: "contact",
  Qualification: "qualification",
  Proposal: "proposal",
  Negotiation: "negotiation",
  Won: "won",
  Lost: "lost",
};


export function pipelineStageLabel(t, stage) {
  const key = stageKeys[stage?.name];
  return key ? t(`deals.stages.${key}`) : stage?.name ?? t("deals.unknownReference");
}
