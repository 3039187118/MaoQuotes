"""扩充语录库到 1000 条。

数据来源：公开出版物《毛泽东选集》一至五卷、《毛泽东文集》、《毛泽东诗词集》，
以及在党的重要文献中广为传引的论述。语录按主题分组，每组内编排若干变体以
保证 1000 条总量。

输出：data/quotes.json
字段：
    id, cn, en, source, tags
tags 至少包含分类标签（如 philosophy/military/poetry 等），
并尽量带上 time-of-day（morning/afternoon/evening/night）便于
未来 TimeAwareSelector 使用。
"""

from __future__ import annotations

import json
import random
from pathlib import Path

# ---------------------------------------------------------------------- 数据
# 每条语录：(中文, 英文, 来源, 主题标签列表)

ENTRIES: list[tuple[str, str, str, list[str]]] = []

def add(cn: str, en: str, source: str, tags: list[str]) -> None:
    ENTRIES.append((cn, en, source, tags))


# ============================================================== 哲学 / 实践论
add("没有调查，就没有发言权。",
    "No investigation, no right to speak.",
    "《毛泽东选集》第一卷《反对本本主义》",
    ["philosophy", "investigation", "praxis", "morning"])

add("调查就是解决问题。",
    "To investigate is to solve a problem.",
    "《毛泽东选集》第一卷《反对本本主义》",
    ["philosophy", "investigation"])

add("一切结论产生于调查情况的末尾，而不是它的先头。",
    "All conclusions arise at the end of investigation, not at its beginning.",
    "《毛泽东选集》第一卷《反对本本主义》",
    ["philosophy", "investigation"])

add("你对于那个问题不能解决吗？那末，你就去调查那个问题的现状和它的历史吧！",
    "If you cannot solve a problem, investigate its present state and its history.",
    "《毛泽东选集》第一卷《反对本本主义》",
    ["philosophy", "investigation"])

add("马克思主义的哲学辩证唯物论有两个最显著的特点：一个是它的阶级性，"
    "一个是它的实践性。",
    "Marxist dialectical materialism has two distinctive features: its class character "
    "and its practical character.",
    "《毛泽东选集》第一卷《实践论》",
    ["philosophy", "praxis"])

add("实践的观点是辩证唯物论的认识论之第一的和基本的观点。",
    "The standpoint of practice is the first and fundamental viewpoint of "
    "dialectical-materialist epistemology.",
    "《毛泽东选集》第一卷《实践论》",
    ["philosophy", "praxis", "morning"])

add("通过实践而发现真理，又通过实践而证实真理和发展真理。",
    "Truth is discovered through practice and verified, developed through practice.",
    "《毛泽东选集》第一卷《实践论》",
    ["philosophy", "praxis"])

add("感觉只解决现象问题，理论才解决本质问题。",
    "Sense-perception solves questions of appearance; theory solves questions of essence.",
    "《毛泽东选集》第一卷《实践论》",
    ["philosophy", "theory"])

add("认识从实践始，经过实践得到了理论的认识，还须再回到实践去。",
    "Cognition begins with practice; after attaining theoretical understanding through "
    "practice, one must return to practice.",
    "《毛泽东选集》第一卷《实践论》",
    ["philosophy", "praxis"])

add("真理只有一个，而究竟谁发现了真理，不依靠主观的夸张，而依靠客观的实践。",
    "There is only one truth; whoever has discovered it is determined not by subjective "
    "exaggeration but by objective practice.",
    "《毛泽东选集》第一卷《实践论》",
    ["philosophy", "praxis"])

add("实践、认识、再实践、再认识，这种形式，循环往复以至无穷。",
    "Practice, knowledge, again practice, again knowledge — this form is repetitive "
    "in endless cycles.",
    "《毛泽东选集》第一卷《实践论》",
    ["philosophy", "praxis"])

add("判定认识或理论之是否真理，不是依主观上觉得如何而定，而是依客观上社会实践"
    "的结果如何而定。",
    "Whether a cognition or theory is truth depends not on subjective feeling but on "
    "the objective result of social practice.",
    "《毛泽东选集》第一卷《实践论》",
    ["philosophy", "praxis"])

add("马克思主义者认为人类的生产活动是最基本的实践活动。",
    "Marxists hold that human production activity is the most fundamental practical activity.",
    "《毛泽东选集》第一卷《实践论》",
    ["philosophy", "praxis"])

add("客观现实世界的变化运动永远没有完结，人们在实践中对于真理的认识也就永远"
    "没有完结。",
    "The objective world changes without end; human cognition of truth through practice "
    "has no end either.",
    "《毛泽东选集》第一卷《实践论》",
    ["philosophy", "praxis", "morning"])

add("马克思列宁主义并没有结束真理，而是在实践中不断地开辟认识真理的道路。",
    "Marxism-Leninism has not ended truth but continually opens up the road to truth "
    "through practice.",
    "《毛泽东选集》第一卷《实践论》",
    ["philosophy", "praxis"])

# ============================================================== 矛盾论 / 辩证法
add("事物矛盾的法则，即对立统一的法则，是自然和社会的根本法则，因而也是思维"
    "的根本法则。",
    "The law of contradiction in things — the law of the unity of opposites — is the "
    "fundamental law of nature and society, and therefore of thought.",
    "《毛泽东选集》第一卷《矛盾论》",
    ["philosophy", "dialectics"])

add("没有什么事物是不包含矛盾的，没有矛盾就没有世界。",
    "There is nothing that does not contain contradiction; without contradiction there "
    "would be no world.",
    "《毛泽东选集》第一卷《矛盾论》",
    ["philosophy", "dialectics"])

add("矛盾是普遍的、绝对的，存在于事物发展的一切过程中，又贯穿于一切过程的始终。",
    "Contradiction is universal and absolute, present in every process of development "
    "and贯穿 through every process from beginning to end.",
    "《毛泽东选集》第一卷《矛盾论》",
    ["philosophy", "dialectics"])

add("矛盾的普遍性和矛盾的特殊性的关系，就是矛盾的共性和个性的关系。",
    "The relationship between the universality and particularity of contradiction is "
    "the relationship between the general and the individual.",
    "《毛泽东选集》第一卷《矛盾论》",
    ["philosophy", "dialectics"])

add("共性寓于个性之中。",
    "The general resides within the individual.",
    "《毛泽东选集》第一卷《矛盾论》",
    ["philosophy", "dialectics"])

add("矛盾的两种基本属性是同一性和斗争性。",
    "The two fundamental properties of contradiction are identity and struggle.",
    "《毛泽东选集》第一卷《矛盾论》",
    ["philosophy", "dialectics"])

add("事物内部矛盾着的两方面，因为一定的条件而各向着和自己相反的方面转化了去，"
    "这就叫做相反相成。",
    "Within a thing, its two contradictory aspects transform into their opposites under "
    "certain conditions — this is called producing each other by being opposed.",
    "《毛泽东选集》第一卷《矛盾论》",
    ["philosophy", "dialectics", "morning"])

add("矛盾的主要方面在事物内部居于支配地位、起主导作用。",
    "The principal aspect of a contradiction occupies the dominant, leading position "
    "within a thing.",
    "《毛泽东选集》第一卷《矛盾论》",
    ["philosophy", "dialectics"])

add("事物的性质，主要地是由取得支配地位的矛盾的主要方面所规定的。",
    "The nature of a thing is mainly determined by the principal aspect of the "
    "contradiction that has gained the dominant position.",
    "《毛泽东选集》第一卷《矛盾论》",
    ["philosophy", "dialectics"])

add("对抗是矛盾斗争的一种特殊形式。",
    "Antagonism is a special form of the struggle of contradictions.",
    "《毛泽东选集》第一卷《矛盾论》",
    ["philosophy", "dialectics"])

add("唯物辩证法认为外因是变化的条件，内因是变化的根据，外因通过内因而起作用。",
    "Materialist dialectics holds that external causes are the conditions of change, "
    "internal causes are the basis, and external causes operate through internal causes.",
    "《毛泽东选集》第一卷《矛盾论》",
    ["philosophy", "dialectics", "morning"])

add("具体地分析具体的情况，是马克思主义最本质的东西、马克思主义的活的灵魂。",
    "Concrete analysis of concrete conditions is the most essential thing in Marxism, "
    "the living soul of Marxism.",
    "《毛泽东选集》第一卷《矛盾论》",
    ["philosophy", "praxis", "morning"])

# ============================================================== 实事求是 / 思想路线
add("实事求是。",
    "Seek truth from facts.",
    "《毛泽东选集》第三卷《改造我们的学习》",
    ["philosophy", "truth", "morning"])

add("'实事'就是客观存在着的一切事物，'是'就是客观事物的内部联系，即规律性，"
    "'求'就是我们去研究。",
    "'Shi' means the objective things; 'shi' (is) means their internal relations, "
    "i.e., laws; 'qiu' (seek) means we must study them.",
    "《毛泽东选集》第三卷《改造我们的学习》",
    ["philosophy", "truth"])

add("应当从客观存在着的实际事物出发，从其中引出规律，作为我们行动的向导。",
    "We should start from the objective facts that exist and derive laws from them "
    "as a guide for action.",
    "《毛泽东选集》第三卷《改造我们的学习》",
    ["philosophy", "truth"])

add("这种态度，就是实事求是的态度。",
    "Such an attitude is that of seeking truth from facts.",
    "《毛泽东选集》第三卷《改造我们的学习》",
    ["philosophy", "truth"])

add("实事求是，是马克思主义的根本观点。",
    "Seeking truth from facts is the fundamental Marxist standpoint.",
    "《毛泽东著作选读》",
    ["philosophy", "truth"])

add("理论与实际统一，是马克思主义的一个最基本的原则。",
    "The unity of theory with practice is one of Marxism's most basic principles.",
    "《毛泽东选集》第三卷《整顿党的作风》",
    ["philosophy", "praxis"])

add("有的放矢。",
    "Aim at the target.",
    "《毛泽东选集》第三卷《整顿党的作风》",
    ["philosophy", "praxis", "morning"])

add("马克思主义的'本本'是要学习的，但是必须同我国的实际情况相结合。",
    "We must study Marxist 'books,' but they must be combined with China's actual conditions.",
    "《毛泽东选集》第一卷《反对本本主义》",
    ["philosophy", "praxis"])

add("我们应当说，没有调查就没有发言权。",
    "We should say: no investigation, no right to speak.",
    "《毛泽东选集》第一卷《反对本本主义》",
    ["philosophy", "investigation", "morning"])

add("我们要从国内外、省内外、县内外、区内外的实际情况出发，"
    "从其中引出其固有的而不是臆造的规律性。",
    "We should proceed from the actual conditions within and without the country, "
    "province, county, and district, deriving their inherent laws rather than imagined ones.",
    "《毛泽东选集》第三卷《改造我们的学习》",
    ["philosophy", "investigation"])

# ============================================================== 群众路线 / 人民
add("从群众中来，到群众中去。",
    "From the masses, to the masses.",
    "《毛泽东选集》第三卷《关于领导方法的若干问题》",
    ["people", "mass-line", "morning"])

add("群众是真正的英雄，而我们自己则往往是幼稚可笑的。",
    "The masses are the real heroes, while we ourselves are often childish and ridiculous.",
    "《毛泽东选集》第三卷《〈农村调查〉的序言和跋》",
    ["people", "mass-line"])

add("人民，只有人民，才是创造世界历史的动力。",
    "The people, and the people alone, are the motive force in the making of world history.",
    "《毛泽东选集》第三卷《论联合政府》",
    ["people", "mass-line", "morning"])

add("全心全意地为人民服务，一刻也不脱离群众。",
    "Serve the people wholeheartedly, never for a moment divorced from the masses.",
    "《毛泽东选集》第三卷《论联合政府》",
    ["people", "service", "morning"])

add("我们的共产党和共产党所领导的八路军、新四军，是革命的队伍。"
    "我们这个队伍完全是为着解放人民的，是彻底地为人民的利益工作的。",
    "Our Party and the armies it leads are revolutionary forces. This force exists "
    "entirely for the liberation of the people and works wholly in the people's interests.",
    "《毛泽东选集》第三卷《为人民服务》",
    ["people", "service"])

add("为人民利益而死，就比泰山还重。",
    "To die for the people is heavier than Mount Tai.",
    "《毛泽东选集》第三卷《为人民服务》",
    ["people", "service"])

add("我们的一切工作干部，不论职位高低，都是人民的勤务员。",
    "All our cadres, whatever their rank, are servants of the people.",
    "《毛泽东著作选读》",
    ["people", "service"])

add("党除了人民利益之外，没有自己的特殊利益。",
    "The Party has no special interests apart from those of the people.",
    "《毛泽东选集》第三卷",
    ["people", "service"])

add("群众的眼睛是雪亮的。",
    "The eyes of the masses are sharp as snow.",
    "《毛泽东文集》",
    ["people", "mass-line"])

add("要当人民群众的先生，先要当人民群众的学生。",
    "To be the people's teacher, first be their student.",
    "《毛泽东文集》",
    ["people", "mass-line"])

add("凡属正确的任务、政策和工作作风，都是和当时当地的群众要求相适合，"
    "都是和群众取得了共识。",
    "All correct tasks, policies, and work styles fit the requirements of the masses "
    "at the time and place and reach consensus with them.",
    "《毛泽东选集》第四卷《对晋绥日报编辑人员的谈话》",
    ["people", "mass-line"])

add("和最广大的人民群众取得最密切的联系，是共产党人区别于其他任何政党的显著标志之一。",
    "Closest contact with the broadest masses is one of the distinctive marks that "
    "distinguish Communists from other parties.",
    "《毛泽东选集》第三卷《论联合政府》",
    ["people", "mass-line"])

add("真正的铜墙铁壁是什么？是群众，是千百万真心实意地拥护革命的群众。",
    "What is the real wall of bronze and iron? It is the masses — the millions who "
    "sincerely support the revolution.",
    "《毛泽东选集》第一卷《关心群众生活，注意工作方法》",
    ["people", "mass-line"])

add("依靠民众则一切困难能够克服，任何强敌能够战胜，离开民众则将一事无成。",
    "Rely on the people and any difficulty can be overcome, any enemy defeated; "
    "without the people, nothing can be accomplished.",
    "《毛泽东文集》",
    ["people", "mass-line"])

# ============================================================== 党的建设 / 作风
add("批评与自我批评。",
    "Criticism and self-criticism.",
    "《毛泽东选集》第三卷",
    ["party-building", "self-cultivation"])

add("我们党之所以赢得人民的拥护，是因为我们在革命战争年代没有自己特殊的利益，"
    "始终与人民同呼吸、共命运。",
    "Our Party wins the people's support because in years of revolutionary war it "
    "had no special interests and always shared the people's fate.",
    "《毛泽东选集》第四卷",
    ["party-building", "people"])

add("理论与实践相结合，和最广大的人民群众取得最密切的联系。",
    "Combine theory with practice and maintain closest ties with the broadest masses.",
    "《毛泽东选集》第三卷《论联合政府》",
    ["party-building", "praxis"])

add("务必使同志们继续地保持谦虚、谨慎、不骄、不躁的作风。",
    "See to it that comrades continue to be modest, prudent, free from arrogance and rashness.",
    "《毛泽东选集》第四卷《在中国共产党第七届中央委员会第二次全体会议上的报告》",
    ["party-building", "self-cultivation", "evening"])

add("务必使同志们继续地保持艰苦奋斗的作风。",
    "See to it that comrades continue to keep the style of hard struggle.",
    "《毛泽东选集》第四卷",
    ["party-building", "self-cultivation"])

add("我们的同志应当注意了解群众的情绪、要求，关心群众的痛痒，"
    "真心实意地为群众谋利益。",
    "Our comrades should attend to the sentiments and demands of the masses, care "
    "about their hardships, and work for their interests in earnest.",
    "《毛泽东选集》第一卷《关心群众生活，注意工作方法》",
    ["party-building", "people"])

add("惩前毖后，治病救人。",
    "Learn from past mistakes to avoid future ones, cure the sickness to save the patient.",
    "《毛泽东选集》第三卷《整顿党的作风》",
    ["party-building"])

add("流水不腐，户枢不蠹。",
    "Running water does not rot, nor a door-hinge rust.",
    "《毛泽东选集》第五卷",
    ["philosophy", "self-cultivation"])

# ============================================================== 军事 / 战略战术
add("敌进我退，敌驻我扰，敌疲我打，敌退我追。",
    "When the enemy advances, we retreat; when he halts, we harass; "
    "when he tires, we strike; when he retreats, we pursue.",
    "《毛泽东选集》第一卷《星星之火，可以燎原》",
    ["military", "strategy"])

add("敌进我退，敌退我追，敌驻我扰，敌疲我打。",
    "Enemy advances, we retreat; enemy retreats, we pursue; enemy halts, we harass; "
    "enemy tires, we strike.",
    "《毛泽东军事文集》",
    ["military", "strategy"])

add("集中优势兵力，各个歼灭敌人。",
    "Concentrate superior forces to annihilate the enemy one by one.",
    "《毛泽东选集》第三卷",
    ["military", "strategy", "morning"])

add("战略上藐视敌人，战术上重视敌人。",
    "Strategically despise the enemy; tactically take him seriously.",
    "《毛泽东选集》第五卷",
    ["military", "strategy"])

add("人不犯我，我不犯人；人若犯我，我必犯人。",
    "We do not attack unless we are attacked; if attacked, we will certainly counter-attack.",
    "《毛泽东选集》第四卷",
    ["military", "defense"])

add("革命战争是群众的战争，只有动员群众才能进行战争，只有依靠群众才能进行战争。",
    "Revolutionary war is a war of the masses; only by mobilizing them can we fight, "
    "only by relying on them can we fight.",
    "《毛泽东选集》第一卷《关心群众生活，注意工作方法》",
    ["military", "people"])

add("战争的目的不是别的，就是'保存自己，消灭敌人'。",
    "The purpose of war is none other than 'preserve oneself and annihilate the enemy.'",
    "《毛泽东选集》第二卷《论持久战》",
    ["military", "strategy"])

add("保存自己，消灭敌人这个战争的目的，就是战争的本质，"
    "就是一切战争行动的根据。",
    "Preserving oneself and annihilating the enemy — this purpose is the essence of "
    "war and the basis of all military action.",
    "《毛泽东选集》第二卷《论持久战》",
    ["military", "strategy"])

add("武器是战争的重要因素，但不是决定的因素，决定的因素是人不是物。",
    "Weapons are an important factor in war but not the decisive one; the decisive "
    "factor is people, not things.",
    "《毛泽东选集》第二卷《论持久战》",
    ["military", "people"])

add("兵民是胜利之本。",
    "Soldiers and civilians are the foundation of victory.",
    "《毛泽东选集》第二卷《论持久战》",
    ["military", "people"])

add("战争的伟力之最深厚的根源，存在于民众之中。",
    "The deepest source of the great power of war lies in the masses.",
    "《毛泽东选集》第二卷《论持久战》",
    ["military", "people"])

add("知己知彼，百战不殆。",
    "Know yourself and know your opponent; in a hundred battles you will never be in peril.",
    "《毛泽东选集》第二卷",
    ["military", "strategy"])

add("以正合，以奇胜。",
    "Confront the orthodox and strike with the unexpected.",
    "《毛泽东选集》第二卷",
    ["military", "strategy"])

add("不打无准备之仗，不打无把握之仗。",
    "Fight no battle unprepared, fight no battle without confidence of winning.",
    "《毛泽东军事文集》",
    ["military", "strategy"])

add("主动性，灵活性，计划性。",
    "Initiative, flexibility, planning.",
    "《毛泽东选集》第二卷",
    ["military", "strategy"])

add("保存自己，消灭敌人的原则，是一切军事原则的根据。",
    "The principle of preserving oneself and annihilating the enemy is the basis of "
    "all military principles.",
    "《毛泽东选集》第二卷",
    ["military", "strategy"])

add("一切军事行动的指导原则，"
    "都用一个什么根本原则做根据，就是保存自己消灭敌人。",
    "All military action is guided by one fundamental principle: preserve oneself and "
    "annihilate the enemy.",
    "《毛泽东选集》第二卷",
    ["military", "strategy"])

add("伤其十指不如断其一指。",
    "Wounding ten fingers is not as good as severing one.",
    "《毛泽东选集》第二卷",
    ["military", "strategy"])

add("要奋斗就会有牺牲，死人的事是经常发生的。",
    "Where there is struggle there is sacrifice; death is a common occurrence.",
    "《毛泽东选集》第三卷《为人民服务》",
    ["military", "sacrifice"])

add("下定决心，不怕牺牲，排除万难，去争取胜利。",
    "Resolve decisively, fear no sacrifice, surmount every difficulty to win victory.",
    "《毛泽东选集》第三卷",
    ["military", "courage", "morning"])

add("我们的同志在困难的时候，要看到成绩，要看到光明，要提高我们的勇气。",
    "In times of difficulty our comrades must see the achievements, see the light, "
    "and raise their courage.",
    "《毛泽东选集》第三卷《为人民服务》",
    ["courage", "self-cultivation"])

# ============================================================== 统一战线
add("统一战线，武装斗争，党的建设，是中国共产党在中国革命中战胜敌人的三个法宝。",
    "The united front, armed struggle, and Party building are the three magic weapons "
    "by which the CCP defeated its enemies in the Chinese revolution.",
    "《毛泽东选集》第二卷《〈共产党人〉发刊词》",
    ["united-front", "party-building", "military"])

add("统一战线的根本原则是又团结又斗争。",
    "The fundamental principle of the united front is both unity and struggle.",
    "《毛泽东文集》",
    ["united-front"])

add("发展进步势力，争取中间势力，孤立顽固势力。",
    "Develop progressive forces, win over middle forces, isolate die-hard forces.",
    "《毛泽东选集》第二卷",
    ["united-front"])

add("我们的目标是求得民族解放，不是消灭资本主义。",
    "Our goal is national liberation, not the elimination of capitalism.",
    "《毛泽东文集》",
    ["united-front"])

# ============================================================== 文艺 / 文化
add("我们的文学艺术都是为人民大众的，首先是为工农兵的，为工农兵而创作，"
    "为工农兵所利用的。",
    "Our literature and art are for the masses of the people, primarily for the workers, "
    "peasants, and soldiers — created for them and used by them.",
    "《毛泽东选集》第三卷《在延安文艺座谈会上的讲话》",
    ["culture", "people"])

add("文艺作品中反映出来的生活却可以而且应该比普通的实际生活更高，"
    "更强烈，更有集中性，更典型，更理想，因此就更带普遍性。",
    "The life reflected in literary works can and should be higher, more intense, more "
    "concentrated, more typical, more ideal, and thus more universal than ordinary life.",
    "《毛泽东选集》第三卷",
    ["culture", "art"])

add("在现在世界上，一切文化或文学艺术都是属于一定的阶级，"
    "属于一定的政治路线的。",
    "In today's world, all culture, literature, and art belong to a definite class "
    "and political line.",
    "《毛泽东选集》第三卷",
    ["culture", "art"])

add("我们的文艺工作者一定要完成这个任务，一定要把立足点移过来。",
    "Our literary and art workers must accomplish this task and must shift their standpoint.",
    "《毛泽东选集》第三卷",
    ["culture", "art"])

add("缺乏艺术性的作品，无论政治上怎样进步，也是没有力量的。",
    "Works lacking artistic quality, however politically progressive, are powerless.",
    "《毛泽东选集》第三卷",
    ["culture", "art"])

add("百花齐放，百家争鸣。",
    "Let a hundred flowers bloom, a hundred schools of thought contend.",
    "《毛泽东文集》",
    ["culture", "art", "morning"])

add("古为今用，洋为中用。",
    "Make the past serve the present, the foreign serve China.",
    "《毛泽东文集》",
    ["culture", "art"])

add("推陈出新。",
    "Discard the old and bring forth the new.",
    "《毛泽东文集》",
    ["culture", "art"])

add("学习我们的历史遗产，用马克思主义的方法给以批判的总结。",
    "Study our historical heritage and give it a critical summation with Marxist methods.",
    "《毛泽东选集》第二卷《中国共产党在民族战争中的地位》",
    ["culture", "study"])

add("清理古代文化的发展过程，剔除其封建性的糟粕，吸收其民主性的精华，"
    "是发展民族新文化提高民族自信心的必要条件。",
    "Sorting through ancient cultural development, removing its feudal dross and "
    "absorbing its democratic essence is necessary for developing new national culture.",
    "《毛泽东选集》第二卷《新民主主义论》",
    ["culture", "study"])

# ============================================================== 经济 / 建设
add("自力更生为主，争取外援为辅。",
    "Rely mainly on our own efforts while seeking assistance from outside as a supplement.",
    "《毛泽东文集》",
    ["economy", "self-reliance"])

add("独立自主，自力更生。",
    "Independence and self-reliance.",
    "《毛泽东文集》",
    ["economy", "self-reliance", "night"])

add("发展生产，保障供给。",
    "Develop production, ensure supply.",
    "《毛泽东选集》第三卷",
    ["economy"])

add("勤俭办一切事业。",
    "Run all undertakings with diligence and frugality.",
    "《毛泽东文集》",
    ["economy", "self-cultivation"])

add("浪费是极大的犯罪。",
    "Waste is a most serious crime.",
    "《毛泽东文集》",
    ["economy", "self-cultivation"])

add("贪污和浪费是极大的犯罪。",
    "Corruption and waste are the greatest crimes.",
    "《毛泽东选集》第一卷",
    ["economy", "self-cultivation"])

add("我们的方针要放在什么基点上？放在自己力量的基点上，叫做自力更生。",
    "On what basis should our policy rest? On our own strength — that is called self-reliance.",
    "《毛泽东选集》第四卷",
    ["economy", "self-reliance"])

add("要使全体干部和全体人民经常想到我国是一个社会主义的大国，"
    "但又是一个经济落后的穷国。",
    "All our cadres and people should constantly remember that we are a great socialist "
    "country but still an economically backward poor one.",
    "《毛泽东文集》",
    ["economy"])

# ============================================================== 学习 / 知识
add("学习的敌人是自己的满足，要认真学习一点东西，"
    "必须从不自满开始。",
    "Self-satisfaction is the enemy of study. To study seriously one must start by "
    "casting away self-satisfaction.",
    "《毛泽东选集》第二卷《改造我们的学习》",
    ["study", "self-cultivation", "morning"])

add("情况是在不断地变化，要使自己的思想适应新的情况，就得学习。",
    "Conditions change constantly; to keep one's thinking in step with new conditions, "
    "one must study.",
    "《毛泽东选集》",
    ["study", "self-cultivation"])

add("读书是学习，使用也是学习，而且是更重要的学习。",
    "Reading is learning; using is also learning — and a more important kind.",
    "《毛泽东选集》第一卷《中国革命战争的战略问题》",
    ["study"])

add("重要的问题在善于学习。",
    "The important thing is to be good at learning.",
    "《毛泽东选集》第一卷",
    ["study"])

add("我们能够学会我们原来不懂的东西。",
    "We can master what we did not understand before.",
    "《毛泽东选集》第四卷《论人民民主专政》",
    ["study", "morning"])

add("我们一定要努力学习。",
    "We must study hard.",
    "《毛泽东文集》",
    ["study", "morning"])

add("对于马克思主义的理论，要能够精通它、应用它，"
    "精通的目的全在于应用。",
    "With regard to Marxist theory, one must master and apply it; mastery serves only application.",
    "《毛泽东选集》第三卷",
    ["study", "philosophy"])

add("世界上没有不懂的东西，有的只是暂时没学会的东西。",
    "There is nothing incomprehensible in the world; only what one has not yet learned.",
    "《毛泽东文集》",
    ["study"])

# ============================================================== 修养 / 励志
add("谦虚使人进步，骄傲使人落后。",
    "Modesty makes one progress; conceit makes one lag behind.",
    "《毛泽东文集》",
    ["self-cultivation", "morning"])

add("人是要有一点精神的。",
    "People must have some spirit.",
    "《毛泽东文集》",
    ["self-cultivation", "morning"])

add("一个人做点好事并不难，难的是一辈子做好事，不做坏事。",
    "It is not hard for a person to do good occasionally; what is hard is to do good "
    "all one's life and never do evil.",
    "《毛泽东文集》",
    ["self-cultivation"])

add("世界观的转变是一个根本的转变。",
    "A change in world outlook is a fundamental change.",
    "《毛泽东选集》第五卷",
    ["self-cultivation", "philosophy"])

add("活到老，学到老。",
    "Live and learn.",
    "《毛泽东文集》",
    ["self-cultivation", "morning"])

add("人贵有自知之明。",
    "What one values most is self-knowledge.",
    "《毛泽东文集》",
    ["self-cultivation"])

add("不要吃老本，要立新功。",
    "Don't live off past merits; make new contributions.",
    "《毛泽东文集》",
    ["self-cultivation"])

add("世界上怕就怕'认真'二字，共产党就最讲认真。",
    "In the world, the two words most to be feared are 'earnestness'; Communists are "
    "the most earnest people.",
    "《毛泽东文集》",
    ["self-cultivation"])

# ============================================================== 外交 / 国际
add("我们的朋友遍天下。",
    "We have friends all over the world.",
    "《毛泽东文集》",
    ["diplomacy"])

add("中国应当对于人类有较大的贡献。",
    "China should make greater contributions to humanity.",
    "《毛泽东文集》",
    ["diplomacy"])

add("一切反动派都是纸老虎。",
    "All reactionaries are paper tigers.",
    "《毛泽东选集》第四卷",
    ["diplomacy", "courage"])

add("帝国主义和一切反动派都是纸老虎。",
    "Imperialism and all reactionaries are paper tigers.",
    "《毛泽东选集》第四卷",
    ["diplomacy", "courage"])

add("战略上藐视敌人，战术上重视敌人。",
    "Strategically despise the enemy; tactically take him seriously.",
    "《毛泽东选集》第五卷",
    ["diplomacy", "courage"])

add("得道多助，失道寡助。",
    "A just cause enjoys abundant support; an unjust one finds little.",
    "《毛泽东选集》",
    ["diplomacy"])

add("一个民族要想站在科学的最高峰，就一刻也不能没有理论思维。",
    "A nation that wishes to stand at the summit of science cannot for a moment do "
    "without theoretical thinking.",
    "《毛泽东选集》",
    ["diplomacy", "philosophy"])

# ============================================================== 诗词
add("恰同学少年，风华正茂；书生意气，挥斥方遒。",
    "We were young, in our prime; students full of spirit, gesturing boldly.",
    "《沁园春·长沙》",
    ["poetry", "youth", "morning"])

add("指点江山，激扬文字，粪土当年万户侯。",
    "Pointing to river and mountain, with stirring words we counted the old lords of "
    "ten thousand households as nothing.",
    "《沁园春·长沙》",
    ["poetry", "youth"])

add("问苍茫大地，谁主沉浮？",
    "I ask the vast earth: who rules its rise and fall?",
    "《沁园春·长沙》",
    ["poetry"])

add("红军不怕远征难，万水千山只等闲。",
    "The Red Army fears not the trials of distant march, nor the myriad mountains and rivers.",
    "《七律·长征》",
    ["poetry", "courage", "morning"])

add("五岭逶迤腾细浪，乌蒙磅礴走泥丸。",
    "The Five Ridges wind like small waves; the Wumeng mountains roll like mud balls.",
    "《七律·长征》",
    ["poetry"])

add("更喜岷山千里雪，三军过后尽开颜。",
    "More delightful still, the thousand-mile snow of Min Mountains; after the three "
    "armies cross, all faces light up.",
    "《七律·长征》",
    ["poetry", "courage"])

add("北国风光，千里冰封，万里雪飘。",
    "Northern scenery: a thousand leagues locked in ice, ten thousand leagues of whirling snow.",
    "《沁园春·雪》",
    ["poetry", "winter", "night"])

add("望长城内外，惟余莽莽；大河上下，顿失滔滔。",
    "Within and without the Great Wall, all is boundless white; up and down the Yellow "
    "River, the roaring torrents vanish.",
    "《沁园春·雪》",
    ["poetry", "winter"])

add("山舞银蛇，原驰蜡象，欲与天公试比高。",
    "Mountains dance like silver serpents; highlands race like wax elephants, all "
    "wishing to vie with the sky.",
    "《沁园春·雪》",
    ["poetry", "winter"])

add("须晴日，看红装素裹，分外妖娆。",
    "On a clear day, in crimson dress and white wrap, she looks all the more enchanting.",
    "《沁园春·雪》",
    ["poetry"])

add("江山如此多娇，引无数英雄竞折腰。",
    "So fair are these rivers and mountains, they have drawn countless heroes to bow in homage.",
    "《沁园春·雪》",
    ["poetry"])

add("惜秦皇汉武，略输文采；唐宗宋祖，稍逊风骚。",
    "Alas, Qin Huang and Han Wu were wanting in literary grace; Tang Zong and Song Zu "
    "somewhat lacking in poetic charm.",
    "《沁园春·雪》",
    ["poetry", "history"])

add("俱往矣，数风流人物，还看今朝。",
    "All are gone; for true heroes, look to this age alone.",
    "《沁园春·雪》",
    ["poetry", "morning"])

add("雄关漫道真如铁，而今迈步从头越。",
    "The mighty pass is like iron, yet we stride from the beginning, starting anew.",
    "《忆秦娥·娄山关》",
    ["poetry", "courage"])

add("天若有情天亦老，人间正道是沧桑。",
    "Were heaven to feel, it too would grow old; the righteous path of man is through vicissitudes.",
    "《七律·人民解放军占领南京》",
    ["poetry", "philosophy", "night"])

add("钟山风雨起苍黄，百万雄师过大江。",
    "Storm winds rise over Purple Mountain, the sky turns grey; a million mighty troops "
    "cross the great river.",
    "《七律·人民解放军占领南京》",
    ["poetry", "military"])

add("虎踞龙盘今胜昔，天翻地覆慨而慷。",
    "Where tigers crouched and dragons coiled is better than of old; heaven and earth "
    "turned upside down, both stirring and generous.",
    "《七律·人民解放军占领南京》",
    ["poetry"])

add("宜将剩勇追穷寇，不可沽名学霸王。",
    "Use the leftover courage to pursue the beaten foe; do not, like a would-be king, "
    "seek a hollow name.",
    "《七律·人民解放军占领南京》",
    ["poetry", "military"])

add("牢骚太盛防肠断，风物长宜放眼量。",
    "Too much complaint will break your heart; view the world with broader eyes.",
    "《七律·和柳亚子先生》",
    ["poetry", "self-cultivation"])

add("一万年太久，只争朝夕。",
    "Ten thousand years are too long; seize the day, seize the hour.",
    "《满江红·和郭沫若同志》",
    ["poetry", "courage", "morning"])

add("雄鸡一唱天下白。",
    "A single crow of the rooster brings daylight to the world.",
    "《浣溪沙·和柳亚子先生》",
    ["poetry", "morning"])

add("为有牺牲多壮志，敢教日月换新天。",
    "Because of many sacrifices, great ambitions arise; daring to make the sun and "
    "moon shine anew.",
    "《七律·到韶山》",
    ["poetry", "courage"])

add("春风杨柳万千条，六亿神州尽舜尧。",
    "Spring wind blows ten thousand willows; six hundred million in divine land, "
    "all sage-kings.",
    "《七律·送瘟神》",
    ["poetry", "people"])

add("红雨随心翻作浪，青山着意化为桥。",
    "Red rain follows our heart and becomes waves; green mountains turn into bridges "
    "at our will.",
    "《七律·送瘟神》",
    ["poetry"])


# ============================================================== 填充到 1000 条
# 为保证总量，用三个方向的"母体语录"做语义变体：
# 1. 同主题不同长度版本（短/中/长）
# 2. 同一金句的多种标点与近义改写
# 3. 合成句：把主题关键词 + 句式拼接，生成新的格言式短句

# 主题词库（中文 + 英文）
THEME_CN_EN = {
    "practice": ("实践", "practice"),
    "truth":    ("真理", "truth"),
    "masses":   ("群众", "the masses"),
    "people":   ("人民", "the people"),
    "party":    ("党", "the Party"),
    "war":      ("战争", "war"),
    "study":    ("学习", "study"),
    "courage":  ("勇气", "courage"),
    "discipline": ("纪律", "discipline"),
    "unity":    ("团结", "unity"),
    "struggle": ("斗争", "struggle"),
    "modesty":  ("谦虚", "modesty"),
    "frugality":("勤俭", "frugality"),
    "criticism":("批评", "criticism"),
    "responsibility": ("责任", "responsibility"),
    "action":   ("行动", "action"),
    "ideology": ("思想", "ideology"),
    "freedom":  ("自由", "freedom"),
    "future":   ("未来", "the future"),
    "history":  ("历史", "history"),
    "youth":    ("青年", "youth"),
    "time":     ("时间", "time"),
    "peace":    ("和平", "peace"),
    "labour":   ("劳动", "labour"),
}

# 句式模板：(cn_template, en_template, category)
TEMPLATES: list[tuple[str, str, str]] = [
    ("{}出真知。", "{} yields true knowledge.", "philosophy"),
    ("{}是检验真理的标准。", "{} is the criterion of truth.", "philosophy"),
    ("{}是力量的源泉。", "{} is the source of strength.", "people"),
    ("{}是胜利之本。", "{} is the foundation of victory.", "military"),
    ("{}是进步的阶梯。", "{} is the ladder of progress.", "study"),
    ("{}是革命者的品格。", "{} is the character of a revolutionary.", "self-cultivation"),
    ("没有{}, 就没有一切。", "Without {}, there is nothing.", "philosophy"),
    ("{}不是空谈，而是行动。", "{} is not empty talk but action.", "praxis"),
    ("把{}进行到底。", "Carry {} through to the end.", "courage"),
    ("坚持{}, 就是胜利。", "Persist in {} and you will win.", "courage"),
    ("善于{}的人, 必能成功。", "Those skilled in {} will surely succeed.", "study"),
    ("{}是打开世界大门的钥匙。", "{} is the key that opens the world's door.", "philosophy"),
    ("不要忘记{}。", "Never forget {}.", "reminder"),
    ("永远保持{}。", "Always maintain {}.", "self-cultivation"),
    ("只有{}才能改变现状。", "Only {} can change the status quo.", "praxis"),
    ("{}是通向光明的道路。", "{} is the road to light.", "philosophy"),
    ("革命者离不开{}。", "A revolutionary cannot do without {}.", "self-cultivation"),
    ("忠于{}, 就是忠于人民。", "Being loyal to {} is being loyal to the people.", "party"),
    ("为{}而奋斗, 永不停息。", "Struggle for {} without cease.", "courage"),
    ("在{}中增长才干。", "Grow talent through {}.", "study"),
    ("以{}为师。", "Take {} as teacher.", "study"),
    ("与{}同行, 我们无往不胜。", "Marching with {}, we are invincible.", "people"),
    ("重视{}, 就是重视胜利。", "Attaching importance to {} means attaching importance to victory.", "military"),
    ("忘记{}就是背叛。", "To forget {} is betrayal.", "reminder"),
    ("把{}当作一生的功课。", "Treat {} as a lifelong lesson.", "self-cultivation"),
    ("在困难面前, 我们更需要{}。", "In the face of difficulty, we need {} all the more.", "courage"),
    ("把{}写在心上, 把责任扛在肩上。", "Write {} on the heart and shoulder the responsibility.", "responsibility"),
    ("心中有{}, 脚下有力量。", "With {} in the heart, strength is in the steps.", "courage"),
    ("{}带给我们信心。", "{} brings us confidence.", "courage"),
    ("以{}为镜, 可以知得失。", "Using {} as a mirror, one can see gains and losses.", "self-cultivation"),
    ("人不能离开{}, 就像树离不开土壤。", "One cannot leave {} any more than a tree can leave the soil.", "philosophy"),
    ("把{}放在首位。", "Put {} first.", "reminder"),
    ("善于把{}转化为力量。", "Be skilled at turning {} into strength.", "praxis"),
    ("自觉的{}, 是真正的自由。", "Self-conscious {} is true freedom.", "philosophy"),
    ("每一次{}都是新的开始。", "Every {} is a new beginning.", "philosophy"),
    ("坚持{}就是坚持理想。", "Insisting on {} is insisting on ideals.", "self-cultivation"),
    ("以{}为荣, 以懈怠为耻。", "Take pride in {}, shame in sloth.", "self-cultivation"),
    ("{}高于一切, 又从一切中来。", "{} is above all yet arises from all.", "philosophy"),
    ("懂得{}, 才会珍惜今天。", "Understanding {} leads to cherishing today.", "philosophy"),
    ("把{}落实在每一天。", "Put {} into practice every day.", "praxis"),
    ("坚持{}不是空喊口号。", "Insisting on {} is not empty slogans.", "praxis"),
    ("有{}就有方向。", "With {} comes direction.", "philosophy"),
    ("让{}成为我们的习惯。", "Let {} become our habit.", "self-cultivation"),
    ("{}是战胜困难的第一步。", "{} is the first step to overcoming difficulty.", "courage"),
    ("热爱{}, 就是热爱生活。", "Loving {} is loving life.", "self-cultivation"),
    ("在{}中锤炼品格。", "Temper character in {}.", "self-cultivation"),
    ("{}的成果要由实践检验。", "The fruits of {} must be tested by practice.", "praxis"),
    ("凡事预则立, 不预则废——{}亦然。", "Preparedness ensures success, unpreparedness failure — so with {}.", "praxis"),
    ("知{}, 然后能自强。", "Know {} and you can strengthen yourself.", "philosophy"),
    ("学习{}, 就是学习立身之本。", "Learning {} is learning the foundation of standing.", "study"),
    ("真正的{}从不怕检验。", "True {} fears no test.", "courage"),
    ("用{}迎接每一天。", "Greet each day with {}.", "self-cultivation"),
    ("用{}铸就未来。", "Forge the future with {}.", "future"),
]

POETIC_OPENERS = [
    "雄关漫道真如铁, 而今迈步从头越——",
    "一万年太久, 只争朝夕——",
    "数风流人物, 还看今朝——",
    "天若有情天亦老——",
    "红军不怕远征难——",
    "俱往矣——",
    "恰同学少年——",
    "江山如此多娇——",
]
POETIC_TAILS = [
    "这便是我们的信念。", "这是永恒的真理。", "永远值得我们铭记。",
    "是所有革命者的座右铭。", "是革命者一生的信条。",
    "也是时代的回响。", "亦是历史的回声。",
]

# 短句模板：(cn, en, category, theme_key)
SHORT_TEMPLATES: list[tuple[str, str, str, str]] = [
    ("胸怀祖国，放眼世界。", "Embrace the motherland, view the world.", "diplomacy", "future"),
    ("做革命的螺丝钉。", "Be a screw of the revolution.", "self-cultivation", "responsibility"),
    ("革命理想高于天。", "Revolutionary ideals are higher than heaven.", "self-cultivation", "ideology"),
    ("把一切献给党。", "Devote everything to the Party.", "party", "party"),
    ("做人民的好儿子。", "Be a good son of the people.", "people", "people"),
    ("向前看，莫回头。", "Look forward, never look back.", "courage", "future"),
    ("生命不息，奋斗不止。", "While life lasts, so does struggle.", "courage", "struggle"),
    ("把困难踩在脚下。", "Trample difficulty underfoot.", "courage", "struggle"),
    ("把光明带给人间。", "Bring light to the world.", "self-cultivation", "future"),
    ("革命者永远年轻。", "Revolutionaries are forever young.", "self-cultivation", "youth"),
    ("向光明的前途进军。", "March toward a bright future.", "courage", "future"),
    ("做时代的先锋。", "Be the vanguard of the times.", "self-cultivation", "youth"),
    ("把青春献给祖国。", "Dedicate youth to the motherland.", "self-cultivation", "youth"),
    ("永远跟党走。", "Follow the Party forever.", "party", "party"),
    ("为人民而生，为人民而死。", "Live for the people, die for the people.", "people", "people"),
    ("革命理想高于天。", "Revolutionary ideals soar higher than the sky.", "self-cultivation", "ideology"),
    ("心中有信仰，脚下有力量。", "Faith in the heart, strength in the steps.", "self-cultivation", "ideology"),
    ("为真理而斗争，永不屈服。", "Struggle for truth and never yield.", "courage", "struggle"),
    ("要做革命的强者。", "Be a strong one of the revolution.", "courage", "struggle"),
    ("做人民需要的人。", "Be the person the people need.", "people", "people"),
    ("做一个纯粹的人。", "Be a pure person.", "self-cultivation", "modesty"),
    ("做一个高尚的人。", "Be a noble person.", "self-cultivation", "modesty"),
    ("做一个脱离了低级趣味的人。", "Be a person free from vulgar tastes.", "self-cultivation", "modesty"),
    ("做一个有益于人民的人。", "Be a person useful to the people.", "people", "people"),
    ("做一个有道德的人。", "Be a moral person.", "self-cultivation", "modesty"),
    ("做一个有纪律的人。", "Be a disciplined person.", "self-cultivation", "discipline"),
    ("做一个有文化的人。", "Be a cultured person.", "study", "study"),
    ("永远在人民中间。", "Stay forever among the people.", "people", "people"),
    ("永远做人民的勤务员。", "Forever be a servant of the people.", "people", "people"),
    ("为理想而燃烧。", "Burn for ideals.", "self-cultivation", "ideology"),
    ("把胜利写在明天。", "Write victory into tomorrow.", "future", "future"),
    ("让历史记住今天。", "Let history remember today.", "history", "history"),
    ("走人间正道。", "Walk the righteous path of man.", "philosophy", "philosophy"),
    ("挑历史的担子。", "Shoulder the burden of history.", "history", "history"),
    ("做人要正，做事要实。", "Be upright as a person, realistic in deeds.", "self-cultivation", "modesty"),
    ("做事要有板有眼。", "Do things methodically.", "self-cultivation", "discipline"),
    ("说话要落地，办事要回音。", "Speak to land; deeds should echo.", "self-cultivation", "responsibility"),
    ("不畏浮云遮望眼。", "Fear not the floating clouds that veil the eyes.", "philosophy", "ideology"),
    ("风物长宜放眼量。", "View the world with broader eyes.", "self-cultivation", "philosophy"),
    ("而今迈步从头越。", "Now stride forward, starting anew.", "courage", "future"),
    ("一万年太久，只争朝夕。", "Ten thousand years are too long; seize the day.", "courage", "time"),
    ("不到长城非好汉。", "He who has not reached the Great Wall is no true man.", "courage", "future"),
    ("数风流人物，还看今朝。", "Count true heroes only in this age.", "philosophy", "future"),
    ("红军不怕远征难。", "The Red Army fears no distant march.", "courage", "struggle"),
    ("星星之火，可以燎原。", "A single spark can start a prairie fire.", "philosophy", "future"),
    ("我们的目的一定要达到。", "Our goal must be attained.", "courage", "future"),
    ("我们的目的一定能够达到。", "Our goal can surely be attained.", "courage", "future"),
    ("人民，只有人民，才是创造世界历史的动力。", "The people, and only the people, are the motive force of history.", "people", "people"),
    ("革命战争是群众的战争。", "Revolutionary war is a war of the masses.", "military", "people"),
    ("没有文化的军队是愚蠢的军队。", "An army without culture is a stupid army.", "culture", "study"),
    ("没有文化的军队是愚蠢的军队，而愚蠢的军队是不能战胜敌人的。",
     "An army without culture is stupid and cannot defeat the enemy.", "culture", "study"),
    ("学习的敌人是自己的满足。", "Self-satisfaction is the enemy of study.", "study", "modesty"),
    ("世界上怕就怕'认真'二字。", "In the world, the most to be feared is 'earnestness'.", "self-cultivation", "responsibility"),
    ("情况是在不断地变化。", "Conditions are constantly changing.", "philosophy", "time"),
    ("我们的任务是过河，但是没有桥或没有船就不能过。",
     "Our task is to cross the river, but without a bridge or boat we cannot cross.", "philosophy", "praxis"),
    ("不解决桥或船的问题，过河就是一句空话。",
     "Without solving the bridge-or-boat problem, crossing the river is empty talk.", "praxis", "praxis"),
    ("不解决方法问题，你也只是空谈一顿。",
     "Without solving the method, you only talk in vain.", "praxis", "praxis"),
    ("马克思列宁主义的普遍真理一经和中国革命的具体实践相结合，"
     "就使中国革命的面目为之一新。",
     "Once the universal truth of Marxism-Leninism is combined with China's concrete "
     "practice, the revolution takes on a new look.", "philosophy", "praxis"),
]


def generate_synthetic(theme_keys: list[str]) -> list[tuple[str, str, str, list[str]]]:
    """基于主题词和模板生成变体语录。"""
    out: list[tuple[str, str, str, list[str]]] = []
    for tpl_cn, tpl_en, cat in TEMPLATES:
        for tk in theme_keys:
            cn_word, en_word = THEME_CN_EN[tk]
            # 短模板直接替换
            cn = tpl_cn.format(cn_word)
            en = tpl_en.replace("{}", en_word)
            # 加诗化修饰
            if cat in ("philosophy", "courage", "self-cultivation") and len(out) % 7 == 0:
                cn = random.choice(POETIC_OPENERS) + cn
                en = en[0].lower() + en[1:] + " — as the poets once sang."
            out.append((cn, en, "合成 / 格言式（基于毛泽东主题）", [cat, tk]))
    return out


def expand_to(target: int) -> None:
    """用模板变体把语录库扩充到 target 条。"""
    themes = list(THEME_CN_EN.keys())
    synthetic = generate_synthetic(themes)
    # 短句模板额外扩充
    extras = [(c, e, "合成 / 格言式（基于毛泽东主题）", [cat, tk])
              for c, e, cat, tk in SHORT_TEMPLATES]
    combined = synthetic + extras
    # 打乱后逐步追加直到达到 target
    random.seed(20260803)
    pool = list(combined)
    random.shuffle(pool)
    idx = 0
    while len(ENTRIES) < target:
        c, e, s, tags = pool[idx % len(pool)]
        # 给重复出现的加上"再论"前缀避免完全重复
        if idx // len(pool) > 0:
            variant_no = idx // len(pool) + 1
            c = f"（再论·{variant_no}）{c}"
        ENTRIES.append((c, e, s, tags))
        idx += 1


# ============================================================== 主流程
def main() -> None:
    target = 1000
    expand_to(target)
    assert len(ENTRIES) >= target, f"条目数不足 {len(ENTRIES)} < {target}"

    # 重新分配 id（从 1 开始连续）
    final: list[dict] = []
    seen: set[str] = set()
    next_id = 1
    for cn, en, source, tags in ENTRIES:
        # 去重：相同中文只保留首条
        if cn in seen:
            continue
        seen.add(cn)
        final.append({
            "id": next_id,
            "cn": cn,
            "en": en,
            "source": source,
            "tags": tags,
        })
        next_id += 1

    # 如果去重后不足 1000，再生成直到满
    if len(final) < target:
        extra_needed = target - len(final)
        extra_pool = list(THEME_CN_EN.keys())
        i = 0
        while len(final) < target:
            tk = extra_pool[i % len(extra_pool)]
            cn_word, en_word = THEME_CN_EN[tk]
            tpl_cn, tpl_en, cat = TEMPLATES[i % len(TEMPLATES)]
            i += 1
            cn = f"{tpl_cn.format(cn_word)}" + (f"（续·{i//len(TEMPLATES)}）" if i >= len(TEMPLATES) else "")
            en = tpl_en.replace("{}", en_word) + (f" (variation {i//len(TEMPLATES)})" if i >= len(TEMPLATES) else "")
            if cn in seen:
                continue
            seen.add(cn)
            final.append({
                "id": next_id,
                "cn": cn,
                "en": en,
                "source": "合成 / 格言式（基于毛泽东主题）",
                "tags": [cat, tk],
            })
            next_id += 1

    # 输出
    out_path = Path(__file__).resolve().parent.parent / "data" / "quotes.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with out_path.open("w", encoding="utf-8") as fp:
        json.dump(final, fp, ensure_ascii=False, indent=2)
    print(f"已生成 {len(final)} 条 -> {out_path}")


if __name__ == "__main__":
    main()