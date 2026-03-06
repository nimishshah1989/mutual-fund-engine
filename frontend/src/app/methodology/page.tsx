"use client";

import PageHeader from "@/components/PageHeader";
import OverviewSection from "./OverviewSection";
import QFSScoringSection from "./QFSScoringSection";
import ShortlistSection from "./ShortlistSection";
import FSASSection from "./FSASSection";
import TierActionSection from "./TierActionSection";
import ActionReferenceSection from "./ActionReferenceSection";
import HardOverridesSection from "./HardOverridesSection";
import DataSourcesSection from "./DataSourcesSection";

export default function MethodologyPage() {
  return (
    <div>
      <PageHeader
        emoji="📖"
        title="Scoring Methodology"
        subtitle="How the MF Recommendation Engine evaluates and ranks mutual funds"
      />

      <OverviewSection />
      <QFSScoringSection />
      <ShortlistSection />
      <FSASSection />
      <TierActionSection />
      <ActionReferenceSection />
      <HardOverridesSection />
      <DataSourcesSection />
    </div>
  );
}
