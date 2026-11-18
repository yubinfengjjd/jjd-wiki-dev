// Auto-extracted from nanxstats/ggsci (R/palettes.R)
// Source: https://github.com/nanxstats/ggsci

export interface JournalPalette {
  id: string;
  label: string;
  journal: string;
  category: 'journal' | 'genomics' | 'general';
  kind: 'discrete' | 'continuous';
  colors: string[];
  namedColors: Record<string, string>;
  rScaleColor: string;
  rScaleFill: string;
}

export const GGSCI_PALETTES: JournalPalette[] = [
  {
    id: "NPG",
    label: "NPG",
    journal: "Nature Publishing Group (NPG)",
    category: "journal",
    kind: "discrete",
    colors: ["#E64B35", "#4DBBD5", "#00A087", "#3C5488", "#F39B7F", "#8491B4", "#91D1C2", "#DC0000", "#7E6148", "#B09C85"],
    namedColors: {"Cinnabar": "#E64B35", "Shakespeare": "#4DBBD5", "PersianGreen": "#00A087", "Chambray": "#3C5488", "Apricot": "#F39B7F", "WildBlueYonder": "#8491B4", "MonteCarlo": "#91D1C2", "Monza": "#DC0000", "RomanCoffee": "#7E6148", "Sandrift": "#B09C85"},
    rScaleColor: "ggsci::scale_color_npg()",
    rScaleFill: "ggsci::scale_fill_npg()",
  },
  {
    id: "Nature",
    label: "Nature",
    journal: "Nature (NPG Alias)",
    category: "journal",
    kind: "discrete",
    colors: ["#E64B35", "#4DBBD5", "#00A087", "#3C5488", "#F39B7F", "#8491B4", "#91D1C2", "#DC0000", "#7E6148", "#B09C85"],
    namedColors: {"Cinnabar": "#E64B35", "Shakespeare": "#4DBBD5", "PersianGreen": "#00A087", "Chambray": "#3C5488", "Apricot": "#F39B7F", "WildBlueYonder": "#8491B4", "MonteCarlo": "#91D1C2", "Monza": "#DC0000", "RomanCoffee": "#7E6148", "Sandrift": "#B09C85"},
    rScaleColor: "ggsci::scale_color_npg()",
    rScaleFill: "ggsci::scale_fill_npg()",
  },
  {
    id: "AAAS",
    label: "AAAS",
    journal: "Science (AAAS)",
    category: "journal",
    kind: "discrete",
    colors: ["#3B4992", "#EE0000", "#008B45", "#631879", "#008280", "#BB0021", "#5F559B", "#A20056", "#808180", "#1B1919"],
    namedColors: {"Chambray": "#3B4992", "Red": "#EE0000", "FunGreen": "#008B45", "HoneyFlower": "#631879", "Teal": "#008280", "Monza": "#BB0021", "ButterflyBush": "#5F559B", "FreshEggplant": "#A20056", "Stack": "#808180", "CodGray": "#1B1919"},
    rScaleColor: "ggsci::scale_color_aaas()",
    rScaleFill: "ggsci::scale_fill_aaas()",
  },
  {
    id: "NEJM",
    label: "NEJM (New England Journal of Medicine)",
    journal: "New England Journal of Medicine",
    category: "journal",
    kind: "discrete",
    colors: ["#BC3C29", "#0072B5", "#E18727", "#20854E", "#7876B1", "#6F99AD", "#FFDC91", "#EE4C97"],
    namedColors: {"TallPoppy": "#BC3C29", "DeepCerulean": "#0072B5", "Zest": "#E18727", "Eucalyptus": "#20854E", "WildBlueYonder": "#7876B1", "Gothic": "#6F99AD", "Salomie": "#FFDC91", "FrenchRose": "#EE4C97"},
    rScaleColor: "ggsci::scale_color_nejm()",
    rScaleFill: "ggsci::scale_fill_nejm()",
  },
  {
    id: "Lancet",
    label: "Lancet",
    journal: "The Lancet (Lancet Oncology)",
    category: "journal",
    kind: "discrete",
    colors: ["#00468B", "#ED0000", "#42B540", "#0099B4", "#925E9F", "#FDAF91", "#AD002A", "#ADB6B6", "#1B1919"],
    namedColors: {"CongressBlue": "#00468B", "Red": "#ED0000", "Apple": "#42B540", "BondiBlue": "#0099B4", "TrendyPink": "#925E9F", "MonaLisa": "#FDAF91", "Carmine": "#AD002A", "Edward": "#ADB6B6", "CodGray": "#1B1919"},
    rScaleColor: "ggsci::scale_color_lancet()",
    rScaleFill: "ggsci::scale_fill_lancet()",
  },
  {
    id: "JAMA",
    label: "JAMA (Journal of the American Medical Association)",
    journal: "Journal of the American Medical Association",
    category: "journal",
    kind: "discrete",
    colors: ["#374E55", "#DF8F44", "#00A1D5", "#B24745", "#79AF97", "#6A6599", "#80796B"],
    namedColors: {"Limed Spruce": "#374E55", "Anzac": "#DF8F44", "Cerulean": "#00A1D5", "Apple Blossom": "#B24745", "Acapulco": "#79AF97", "Kimberly": "#6A6599", "Makara": "#80796B"},
    rScaleColor: "ggsci::scale_color_jama()",
    rScaleFill: "ggsci::scale_fill_jama()",
  },
  {
    id: "JCO",
    label: "JCO (Journal of Clinical Oncology)",
    journal: "Journal of Clinical Oncology",
    category: "journal",
    kind: "discrete",
    colors: ["#0073C2", "#EFC000", "#868686", "#CD534C", "#7AA6DC", "#003C67", "#8F7700", "#3B3B3B", "#A73030", "#4A6990"],
    namedColors: {"Lochmara": "#0073C2", "Corn": "#EFC000", "Gray": "#868686", "ChestnutRose": "#CD534C", "Danube": "#7AA6DC", "RegalBlue": "#003C67", "Olive": "#8F7700", "MineShaft": "#3B3B3B", "WellRead": "#A73030", "KashmirBlue": "#4A6990"},
    rScaleColor: "ggsci::scale_color_jco()",
    rScaleFill: "ggsci::scale_fill_jco()",
  },
  {
    id: "BMJ",
    label: "BMJ (British Medical Journal)",
    journal: "British Medical Journal",
    category: "journal",
    kind: "discrete",
    colors: ["#2A6EBB", "#F0AB00", "#C50084", "#7D5CC6", "#E37222", "#69BE28", "#00B2A9", "#CD202C", "#747678"],
    namedColors: {"Blue": "#2A6EBB", "Yellow": "#F0AB00", "Pink": "#C50084", "Purple": "#7D5CC6", "Orange": "#E37222", "Green": "#69BE28", "Aqua": "#00B2A9", "Red": "#CD202C", "Grey": "#747678"},
    rScaleColor: "ggsci::scale_color_bmj()",
    rScaleFill: "ggsci::scale_fill_bmj()",
  },
  {
    id: "Frontiers",
    label: "Frontiers",
    journal: "Frontiers",
    category: "journal",
    kind: "discrete",
    colors: ["#D51317", "#F39200", "#EFD500", "#95C11F", "#007B3D", "#31B7BC", "#0094CD", "#164194", "#6F286A", "#706F6F"],
    namedColors: {"Crimson": "#D51317", "Tangerine": "#F39200", "SchoolBus": "#EFD500", "Citron": "#95C11F", "FunGreen": "#007B3D", "Pelorous": "#31B7BC", "PacificBlue": "#0094CD", "ToryBlue": "#164194", "Plum": "#6F286A", "DoveGrey": "#706F6F"},
    rScaleColor: "ggsci::scale_color_frontiers()",
    rScaleFill: "ggsci::scale_fill_frontiers()",
  },
  {
    id: "UCSCGB",
    label: "UCSCGB (UCSC Genome Browser)",
    journal: "UCSC Genome Browser",
    category: "genomics",
    kind: "discrete",
    colors: ["#FF0000", "#FF9900", "#FFCC00", "#00FF00", "#6699FF", "#CC33FF", "#99991E", "#999999", "#FF00CC", "#CC0000", "#FFCCCC", "#FFFF00", "#CCFF00", "#358000", "#0000CC", "#99CCFF", "#00FFFF", "#CCFFFF", "#9900CC", "#CC99FF", "#996600", "#666600", "#666666", "#CCCCCC", "#79CC3D", "#CCCC99"],
    namedColors: {"chr5": "#FF0000", "chr8": "#FF9900", "chr9": "#FFCC00", "chr12": "#00FF00", "chr15": "#6699FF", "chr20": "#CC33FF", "chr3": "#99991E", "chrX": "#999999", "chr6": "#FF00CC", "chr4": "#CC0000", "chr7": "#FFCCCC", "chr10": "#FFFF00", "chr11": "#CCFF00", "chr13": "#358000", "chr14": "#0000CC", "chr16": "#99CCFF", "chr17": "#00FFFF", "chr18": "#CCFFFF", "chr19": "#9900CC", "chr21": "#CC99FF", "chr1": "#996600", "chr2": "#666600", "chr22": "#666666", "chrY": "#CCCCCC", "chrUn": "#79CC3D", "chrM": "#CCCC99"},
    rScaleColor: "ggsci::scale_color_ucscgb()",
    rScaleFill: "ggsci::scale_fill_ucscgb()",
  },
  {
    id: "LocusZoom",
    label: "LocusZoom",
    journal: "LocusZoom GWAS",
    category: "genomics",
    kind: "discrete",
    colors: ["#D43F3A", "#EEA236", "#5CB85C", "#46B8DA", "#357EBD", "#9632B8", "#B8B8B8"],
    namedColors: {"0.8to1.0": "#D43F3A", "0.6to0.8": "#EEA236", "0.4to0.6": "#5CB85C", "0.2to0.4": "#46B8DA", "0.0to0.2": "#357EBD", "LDRefVar": "#9632B8", "nodata": "#B8B8B8"},
    rScaleColor: "ggsci::scale_color_locuszoom()",
    rScaleFill: "ggsci::scale_fill_locuszoom()",
  },
  {
    id: "IGV",
    label: "IGV",
    journal: "Integrative Genomics Viewer (IGV)",
    category: "genomics",
    kind: "discrete",
    colors: ["#5050FF", "#CE3D32", "#749B58", "#F0E685", "#466983", "#BA6338", "#5DB1DD", "#802268", "#6BD76B", "#D595A7", "#924822", "#837B8D", "#C75127", "#D58F5C", "#7A65A5", "#E4AF69", "#3B1B53", "#CDDEB7", "#612A79", "#AE1F63", "#E7C76F", "#5A655E", "#CC9900", "#99CC00", "#A9A9A9", "#CC9900", "#99CC00", "#33CC00", "#00CC33", "#00CC99", "#0099CC", "#0A47FF", "#4775FF", "#FFC20A", "#FFD147", "#990033", "#991A00", "#996600", "#809900", "#339900", "#00991A", "#009966", "#008099", "#003399", "#1A0099", "#660099", "#990080", "#D60047", "#FF1463", "#00D68F", "#14FFB1"],
    namedColors: {"chr1": "#5050FF", "chr2": "#CE3D32", "chr3": "#749B58", "chr4": "#F0E685", "chr5": "#466983", "chr6": "#BA6338", "chr7": "#5DB1DD", "chr8": "#802268", "chr9": "#6BD76B", "chr10": "#D595A7", "chr11": "#924822", "chr12": "#837B8D", "chr13": "#C75127", "chr14": "#D58F5C", "chr15": "#7A65A5", "chr16": "#E4AF69", "chr17": "#3B1B53", "chr18": "#CDDEB7", "chr19": "#612A79", "chr20": "#AE1F63", "chr21": "#E7C76F", "chr22": "#5A655E", "chrX": "#CC9900", "chrY": "#99CC00", "chrUn": "#A9A9A9", "chr23": "#CC9900", "chr24": "#99CC00", "chr25": "#33CC00", "chr26": "#00CC33", "chr27": "#00CC99", "chr28": "#0099CC", "chr29": "#0A47FF", "chr30": "#4775FF", "chr31": "#FFC20A", "chr32": "#FFD147", "chr33": "#990033", "chr34": "#991A00", "chr35": "#996600", "chr36": "#809900", "chr37": "#339900", "chr38": "#00991A", "chr39": "#009966", "chr40": "#008099", "chr41": "#003399", "chr42": "#1A0099", "chr43": "#660099", "chr44": "#990080", "chr45": "#D60047", "chr46": "#FF1463", "chr47": "#00D68F", "chr48": "#14FFB1"},
    rScaleColor: "ggsci::scale_color_igv()",
    rScaleFill: "ggsci::scale_fill_igv()",
  },
  {
    id: "IGV_Alternating",
    label: "IGV_Alternating (IGV Alternating Chromosomes)",
    journal: "IGV Alternating Chromosomes",
    category: "genomics",
    kind: "discrete",
    colors: ["#5773CC", "#FFB900"],
    namedColors: {"Indigo": "#5773CC", "SelectiveYellow": "#FFB900"},
    rScaleColor: "ggsci::scale_color_igv()",
    rScaleFill: "ggsci::scale_fill_igv()",
  },
  {
    id: "COSMIC_Light",
    label: "COSMIC_Light (COSMIC Hallmarks of Cancer (Light))",
    journal: "COSMIC Hallmarks of Cancer (Light)",
    category: "genomics",
    kind: "discrete",
    colors: ["#2E2A2B", "#CF4E9C", "#8C57A2", "#358DB9", "#82581F", "#2F509E", "#E5614C", "#97A1A7", "#3DA873", "#DC9445"],
    namedColors: {"Invasion and Metastasis": "#2E2A2B", "Escaping Immunic Response to Cancer": "#CF4E9C", "Change of Cellular Energetics": "#8C57A2", "Cell Replicative Immortality": "#358DB9", "Suppression of Growth": "#82581F", "Genome Instability and Mutations": "#2F509E", "Angiogenesis": "#E5614C", "Escaping Programmed Cell Death": "#97A1A7", "Proliferative Signaling": "#3DA873", "Tumour Promoting Inflammation": "#DC9445"},
    rScaleColor: "ggsci::scale_color_cosmic()",
    rScaleFill: "ggsci::scale_fill_cosmic()",
  },
  {
    id: "COSMIC_Dark",
    label: "COSMIC_Dark (COSMIC Hallmarks of Cancer (Dark))",
    journal: "COSMIC Hallmarks of Cancer (Dark)",
    category: "genomics",
    kind: "discrete",
    colors: ["#171717", "#7D0226", "#300049", "#165459", "#3F2327", "#0B1948", "#E71012", "#555555", "#193006", "#A8450C"],
    namedColors: {"Invasion and Metastasis": "#171717", "Escaping Immunic Response to Cancer": "#7D0226", "Change of Cellular Energetics": "#300049", "Cell Replicative Immortality": "#165459", "Suppression of Growth": "#3F2327", "Genome Instability and Mutations": "#0B1948", "Angiogenesis": "#E71012", "Escaping Programmed Cell Death": "#555555", "Proliferative Signaling": "#193006", "Tumour Promoting Inflammation": "#A8450C"},
    rScaleColor: "ggsci::scale_color_cosmic()",
    rScaleFill: "ggsci::scale_fill_cosmic()",
  },
  {
    id: "GSEA",
    label: "GSEA",
    journal: "GSEA GenePattern Heatmap",
    category: "genomics",
    kind: "continuous",
    colors: ["#4500AD", "#2700D1", "#6B58EF", "#8888FF", "#C7C1FF", "#D5D5FF", "#FFC0E5", "#FF8989", "#FF7080", "#FF5A5A", "#EF4040", "#D60C00"],
    namedColors: {"Purple": "#4500AD", "DarkBlue": "#2700D1", "RoyalBlue": "#6B58EF", "Malibu": "#8888FF", "Melrose": "#C7C1FF", "Fog": "#D5D5FF", "CottonCandy": "#FFC0E5", "VividTangerine": "#FF8989", "BrinkPink": "#FF7080", "Persimmon": "#FF5A5A", "Flamingo": "#EF4040", "GuardsmanRed": "#D60C00"},
    rScaleColor: "ggsci::scale_color_gsea()",
    rScaleFill: "ggsci::scale_fill_gsea()",
  },
  {
    id: "D3",
    label: "D3",
    journal: "D3 Category10",
    category: "general",
    kind: "discrete",
    colors: ["#1F77B4", "#FF7F0E", "#2CA02C", "#D62728", "#9467BD", "#8C564B", "#E377C2", "#7F7F7F", "#BCBD22", "#17BECF"],
    namedColors: {"Matisse": "#1F77B4", "Flamenco": "#FF7F0E", "ForestGreen": "#2CA02C", "Punch": "#D62728", "Wisteria": "#9467BD", "SpicyMix": "#8C564B", "Orchid": "#E377C2", "Gray": "#7F7F7F", "KeyLimePie": "#BCBD22", "Java": "#17BECF"},
    rScaleColor: "ggsci::scale_color_d3()",
    rScaleFill: "ggsci::scale_fill_d3()",
  },
  {
    id: "Observable",
    label: "Observable",
    journal: "Observable 10",
    category: "general",
    kind: "discrete",
    colors: ["#4269D0", "#EFB118", "#FF725C", "#6CC5B0", "#3CA951", "#FF8AB7", "#A463F2", "#97BBF5", "#9C6B4E", "#9498A0"],
    namedColors: {"Blue": "#4269D0", "Orange": "#EFB118", "Red": "#FF725C", "Cyan": "#6CC5B0", "Green": "#3CA951", "Pink": "#FF8AB7", "Purple": "#A463F2", "LightBlue": "#97BBF5", "Brown": "#9C6B4E", "Gray": "#9498A0"},
    rScaleColor: "ggsci::scale_color_observable()",
    rScaleFill: "ggsci::scale_fill_observable()",
  },
  {
    id: "Cell",
    label: "Cell (ColorBrewer Set1 Compatible)",
    journal: "Cell Press",
    category: "journal",
    kind: "discrete",
    colors: ["#E41A1C", "#377EB8", "#4DAF4A", "#984EA3", "#FF7F00", "#A65628", "#F781BF", "#999999"],
    namedColors: {"Red": "#E41A1C", "Blue": "#377EB8", "Green": "#4DAF4A", "Purple": "#984EA3", "Orange": "#FF7F00", "Brown": "#A65628", "Pink": "#F781BF", "Grey": "#999999"},
    rScaleColor: "ggplot2::scale_color_brewer(palette = \"Set1\")",
    rScaleFill: "ggplot2::scale_fill_brewer(palette = \"Set1\")",
  },
];

export const DEFAULT_PALETTE_CHOICES = ['NPG', 'Nature', 'Lancet', 'NEJM', 'JAMA', 'AAAS', 'JCO', 'Cell'];

export function paletteFor(name: string): JournalPalette {
  const norm = (name || '').trim().toLowerCase();
  return GGSCI_PALETTES.find((p) => p.id.toLowerCase() === norm) ?? GGSCI_PALETTES[0];
}

export function paletteColorsFor(name: string, count?: number): string[] {
  const colors = paletteFor(name).colors;
  if (!count || count <= 0 || count >= colors.length) return colors;
  return colors.slice(0, count);
}

export function toRScaleCall(name: string, aesthetic: 'color' | 'fill' = 'color'): string {
  const pal = paletteFor(name);
  return aesthetic === 'fill' ? pal.rScaleFill : pal.rScaleColor;
}

export function toPythonPaletteExpr(name: string): string {
  const colors = paletteFor(name).colors;
  return `sns.color_palette(${JSON.stringify(colors)})`;
}
