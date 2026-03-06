"use client";

import PageHeader from "@/components/PageHeader";
import OverviewSection from "./OverviewSection";
import QFSScoringSection from "./QFSScoringSection";
import FSASSection from "./FSASSection";
import TierActionSection from "./TierActionSection";
import ActionReferenceSection from "./ActionReferenceSection";
import HardOverridesSection from "./HardOverridesSection";
import DataSourcesSection from "./DataSourcesSection";

export default function MethodologyPage() {
  return (
    <div>
      <PageHeader
        title="Scoring Methodology"
        subtitle="How the Recommendation Engine evaluates and ranks mutual funds"
      />

      <OverviewSection />
      <QFSScoringSection />
      <FSASSection />
      <TierActionSection />
      <HardOverridesSection />
      <ActionReferenceSection />
      <DataSourcesSection />
    </div>
  );
}
