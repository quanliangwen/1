# 大数据与生成式AI：前4页精美版

本版只调整视觉表现，4页文字、数据、统计时点、案例内容与来源均保持上一版一致。保留原模板的4:3尺寸和北京邮电大学校名校徽页眉。

视觉调整：深蓝与冰蓝配色、立体教学意象、清晰的标题和正文层级、统一深色表格与大数字排版。

PPT中的文字、数字和第3页表格均可编辑。背景和封面插图为嵌入式AI生成图片。4张PNG由最终PPT直接在Microsoft PowerPoint中导出，分辨率1600×1200。

第4页数据来源仍为[CNNIC《生成式人工智能应用发展报告（2026）》](https://www.cnnic.org.cn/n4/2026/1008/c88-11704.html)，统计时点为2026年上半年。完整链接在第4页备注。

## 插图与背景生成记录

使用内置image_gen工具。以下为最终提示词和临时工作区相对资产路径，图片已嵌入交付PPT。

```json
{
  "mode": "built-in image_gen",
  "assets": [
    {
      "path": "reference/cover-premium.png",
      "prompt": "Create a premium academic technology presentation BODY BACKGROUND illustration, landscape aspect ratio 960:622 (approximately 1.543:1). This image will sit beneath an existing university masthead, do not include logos or any text. Luxurious deep midnight navy #071D38 and #0C3156, restrained cyan #69D5EF rim lighting, high-end translucent glass and brushed silver materials. MAIN SUBJECT: four evenly spaced sophisticated 3D still-life groups running horizontally across the LOWER MIDDLE of the image: at x=15% a pair of frosted data documents plus a low silver database cylinder; x=38% a beautifully crafted neural-network sphere made of cyan glass nodes and fine connecting wires; x=61% precision magnifying lens and metallic gear; x=84% a frosted research report document with a subtle cyan bar chart and verification check (all symbols, no words). Each group roughly 18% image width. The groups should occupy vertical 48% to 78% of the image, keeping lower 20% clear for editable labels/presenter, upper 43% calm deep navy clear for overlaid white title and subtitle. Natural continuous flow of very subtle cyan data filaments linking these objects, edge-to-edge studio lighting, elegant editorial composition, physically realistic glossy reflections but not toy-like. Fill the canvas meaningfully without heavy noise. Very faint network grain on far right only. NO letters, NO numbers, NO labels, NO typography, NO panels or cards, NO UI, NO watermarks. Quality suitable for a polished university keynote."
    },
    {
      "path": "reference/body-premium.png",
      "prompt": "Generate a polished academic keynote BODY BACKGROUND, landscape aspect ratio 960:622 (approximately 1.543:1). It is a quiet backdrop for editable text and a table, not a complete slide. Deep midnight navy #071D38 across left 85% with subtle navy depth gradient #0C3156 to the far right. Elegant restrained glowing cyan data filaments and fine network dots ONLY along the far right 12% and bottom 5%, converging into a delicate glassy light bloom at the lower right corner. Most of the image must remain smooth, clean and dark enough for bright white large text. Restrained, premium, sophisticated, clean engineering aesthetic, editorial keynote, luxurious materials, no generic digital globe. Do not create card containers, boxes, borders or placeholder shapes. No text, no letters, no numbers, no logos, no symbols, no watermarks, no large objects in text area. Fully opaque full-bleed background."
    }
  ]
}

```
