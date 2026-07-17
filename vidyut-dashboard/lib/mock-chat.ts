// Scripted bot replies for the chat demo when the Flask backend is not
// hosted. Numbers are the verified KERC 2025 constants and the Nikhil
// persona (210 units, 3 kW, net Rs. 1,943.22) so the demo survives
// scrutiny from anyone who checks the math.

const GREETING = `Namaskara! I'm VidyutMitra, your energy advisor for MESCOM bills.

Send a photo of your electricity bill and I'll explain it in plain language: your charges, subsidies you may be missing, and whether rooftop solar makes sense for you.`;

const ANALYSIS: string[] = [
  `Reading your bill... done! Here's the breakdown:

Units consumed: 210
Sanctioned load: 3 kW

Energy charge (210 x Rs. 5.80): Rs. 1,218.00
Fixed charge (3 kW x Rs. 145): Rs. 435.00
Plus 9% electricity tax, P&G surcharge and FPPCA.

Net bill: Rs. 1,943.22`,
  `Fixed Charge Trap alert: your usage needs only 2 kW, but you pay for 3 kW of sanctioned load. That's Rs. 145 extra every single month.`,
  `Solar check: a 3 kW rooftop system costs about Rs. 1,65,000, and PM Surya Ghar covers Rs. 78,000 of it. At your usage it pays for itself in about 45 months and offsets ~2.98 tonnes of CO2 a year.

On WhatsApp you'd also get this as a Kannada voice note and a savings infographic.`,
];

const SOLAR = `Rooftop solar in short: a 3 kW system costs about Rs. 1,65,000, and the PM Surya Ghar scheme covers Rs. 78,000 of that. Typical payback is about 45 months, followed by roughly 25 years of nearly free power.

Send your bill photo and I'll size a system for your actual usage.`;

const GRUHA_JYOTHI = `Gruha Jyothi gives eligible households free units up to a personal entitlement: your FY22-23 monthly average plus 10 units, capped at 200.

Careful though: cross 200 units in a month and the entire subsidy is lost for that month. Send your bill and I'll check where you stand.`;

const STOP = `Understood. In the live system, STOP permanently deletes your data: your profile and every stored bill, immediately and irreversibly.`;

const DEFAULT = `I'm best with bills! Send a photo of your MESCOM electricity bill using the paperclip, or ask me about "solar" or "Gruha Jyothi".`;

export function getMockReplies(text: string, hasImage: boolean): string[] {
  if (hasImage) {
    return ANALYSIS;
  }
  const t = text.trim().toLowerCase();
  if (/^(hi|hello|hey|namaste|namaskara|start)\b/.test(t)) {
    return [GREETING];
  }
  if (t.includes("solar") || t.includes("surya")) {
    return [SOLAR];
  }
  if (t.includes("gruha") || t.includes("jyothi") || t.includes("subsid") || t === "gj") {
    return [GRUHA_JYOTHI];
  }
  if (t === "stop") {
    return [STOP];
  }
  return [DEFAULT];
}
