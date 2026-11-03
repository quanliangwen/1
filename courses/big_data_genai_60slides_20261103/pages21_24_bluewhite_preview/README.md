# 第21至24页蓝白高清样图

四张4:3高清PNG，沿用蓝白北邮模板，用于确认视觉设计。ZIP仅含四张样图，不是可编辑PPT。

- 第21页：Token与上下文。中英文拆分是概念教学示意，不是特定分词器的精确结果；容量分区不代表真实占比。上下文不等于模型永久记忆，通常需预留输出空间。
- 第22页：使用“后者”和“前者”的指代关系说明关联。句子、箭头、分组均为教学构造，不是实测注意力，也不构成人类理解或意识的证据。
- 第23页：比较预训练、SFT、偏好对齐和RL，说明目标与方法的联系，避免所有模型必经单一路线。使用DPO原论文图1说明RLHF与DPO两条偏好学习路径，原图直接渲染后嵌入。DPO论文发表于2023年，所取为后续arXiv修订版本中的图1。
- 第24页：区分训练更新参数与推理使用已有参数；上下文、输出、工具调用和执行次数影响系统开销。实际机房照片来自Google The Dalles，画面是工作人员排查CPU过热，不是特定模型训练现场，也不用于证明训练或推理的固定成本。

内置image_gen生成版式和教学示意；论文图和真实照片通过内部演示文稿重新嵌入，以保留原始细节。生成提示词见设计生成记录.json。

资料与图像：
- Token拆分：https://huggingface.co/docs/transformers/main/en/tokenizer_summary
- 上下文窗口：https://platform.claude.com/docs/en/build-with-claude/context-windows
- 用户提供的管理上下文研究：https://www.anthropic.com/research/managed-agents
- Transformer：https://arxiv.org/abs/1706.03762
- BERT：https://arxiv.org/abs/1810.04805
- ChatGPT历史训练方法：https://openai.com/index/chatgpt/
- DeepSeek-R1：https://arxiv.org/abs/2501.12948
- DPO论文与图1：https://arxiv.org/abs/2305.18290
- IEA能源与AI：https://www.iea.org/reports/key-questions-on-energy-and-ai/executive-summary
- Google图库：https://www.datacenters.google/discover-more/photo-gallery/
- 运维照片：https://www.gstatic.com/marketing-cms/assets/images/a5/52/bfa668c2406f93820f6780af9525/denise-at-the-dalles.jpg

校验和见SHA256SUMS.txt。
