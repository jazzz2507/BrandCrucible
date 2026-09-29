export interface BrandData {
  sessionId: string;
  stage: string;
  brand: {
    name: string;
    tagline: string;
    positioning: string;
    palette: string[];
    typography: { heading: string; body: string };
  };
  challengeReport: {
    clicheScore: number;
    distinctivenessScore: number;
    verdict: string;
  };
}

export const mockBrandData: BrandData = {
  sessionId: "demo-123",
  stage: "Deliver",
  brand: {
    name: "BrandCrucible",
    tagline: "Forge distinct identities, incinerate clichés.",
    positioning: "An adversarial branding engine for ambitious founders.",
    palette: ["#0B1020", "#121933", "#38BDF8", "#34D399", "#F43F5E"],
    typography: { heading: "Space Grotesk", body: "Inter" },
  },
  challengeReport: {
    clicheScore: 14,
    distinctivenessScore: 92,
    verdict: "Passed challenger review",
  },
};