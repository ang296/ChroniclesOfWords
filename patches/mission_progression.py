from pathlib import Path
import sys
root = Path(sys.argv[1])

def replace(rel, old, new):
    p = root / rel
    s = p.read_text(encoding="utf-8")
    if old not in s:
        raise SystemExit(f"Patch anchor missing: {rel}: {old[:80]!r}")
    p.write_text(s.replace(old, new, 1), encoding="utf-8")

m = "app/src/main/java/ua/chroniclesofwords/MainActivity.kt"
replace(m, '''    var tab by remember { mutableStateOf(Tab.WORLD) }
    var selectedExercise by remember { mutableStateOf<Exercise?>(null) }
''', '''    var tab by remember { mutableStateOf(Tab.WORLD) }
    var selectedExercise by remember { mutableStateOf<Exercise?>(null) }
    var activeMissionIndex by remember { mutableIntStateOf(-1) }
    var selectedExerciseIndex by remember { mutableIntStateOf(0) }
    val missions = remember { GameContent.exercises.groupBy { it.topic }.entries.toList() }
''')
replace(m, '''    BackHandler(enabled = selectedExercise != null) {
        selectedExercise = null
    }
''', '''    BackHandler(enabled = selectedExercise != null) {
        selectedExercise = null
        activeMissionIndex = -1
    }
''')
replace(m, 'onClick = { selectedExercise = null; tab = item }', 'onClick = { selectedExercise = null; activeMissionIndex = -1; tab = item }')
replace(m, '''                    ExerciseScreen(
                        exercise = selectedExercise!!,
                        onBack = { selectedExercise = null },
                        onResult = { correct ->
                            // Capture the topic before launching: the user may leave the
                            // exercise while the database coroutine is still waiting.
                            val completedTopic = selectedExercise?.topic.orEmpty()
                            scope.launch {
                                val current = dao.getOnce() ?: ProgressEntity()
                                dao.save(
                                    current.copy(
                                        xp = current.xp + if (correct) 10 else 2,
                                        completedQuestions = current.completedQuestions + 1,
                                        correctAnswers = current.correctAnswers + if (correct) 1 else 0,
                                        lastTopic = completedTopic
                                    )
                                )
                            }
                        }
                    )
''', '''                    ExerciseScreen(
                        exercise = selectedExercise!!,
                        onBack = { selectedExercise = null; activeMissionIndex = -1 },
                        onContinue = {
                            val mi = activeMissionIndex
                            if (mi >= 0) {
                                val list = missions.getOrNull(mi)?.value.orEmpty()
                                val next = selectedExerciseIndex + 1
                                if (next < list.size) {
                                    selectedExerciseIndex = next
                                    selectedExercise = list[next]
                                } else {
                                    selectedExercise = null
                                    activeMissionIndex = -1
                                }
                            } else selectedExercise = null
                        },
                        onResult = { correct ->
                            val topic = selectedExercise?.topic.orEmpty()
                            val mi = activeMissionIndex
                            val ei = selectedExerciseIndex
                            val count = missions.getOrNull(mi)?.value?.size ?: 0
                            scope.launch {
                                val current = dao.getOnce() ?: ProgressEntity()
                                val inMission = mi >= 0 && mi == current.completedMissions
                                val done = inMission && count > 0 && ei + 1 >= count
                                dao.save(current.copy(
                                    xp = current.xp + if (correct) 10 else 2,
                                    completedQuestions = current.completedQuestions + 1,
                                    correctAnswers = current.correctAnswers + if (correct) 1 else 0,
                                    lastTopic = topic,
                                    currentExerciseIndex = if (inMission && !done) ei + 1 else if (done) 0 else current.currentExerciseIndex,
                                    completedMissions = if (done) current.completedMissions + 1 else current.completedMissions
                                ))
                            }
                        }
                    )
''')
replace(m, '''                        Tab.WORLD -> WorldScreen(
                            onStart = { selectedExercise = GameContent.exercises.first() }
                        )
''', '''                        Tab.WORLD -> WorldScreen(progress = progress, onStart = {
                            val mi = (progress?.completedMissions ?: 0).coerceAtMost(missions.size)
                            val list = missions.getOrNull(mi)?.value.orEmpty()
                            val start = (progress?.currentExerciseIndex ?: 0).coerceIn(0, (list.size - 1).coerceAtLeast(0))
                            if (list.isNotEmpty()) {
                                activeMissionIndex = mi
                                selectedExerciseIndex = start
                                selectedExercise = list[start]
                            }
                        })
''')
replace(m, 'private fun WorldScreen(onStart: () -> Unit) {', '''private fun WorldScreen(progress: ProgressEntity?, onStart: () -> Unit) {
    val missions = remember { GameContent.exercises.groupBy { it.topic }.entries.toList() }
    val completed = (progress?.completedMissions ?: 0).coerceIn(0, missions.size)
    val currentMission = missions.getOrNull(completed)
    val currentExercise = progress?.currentExerciseIndex ?: 0''')
replace(m, '''                    Text("Глава I · Шепіт зруйнованого Архіву", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                    Text("Хранитель просить тебе відновити перші сторінки Бібліотеки Знань.")
                    Button(onClick = onStart, modifier = Modifier.fillMaxWidth()) {
                        Text("Розпочати місію")
                    }
''', '''                    Text("Глава I · Шепіт зруйнованого Архіву", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                    Text("Хранитель просить тебе відновити перші сторінки Бібліотеки Знань.")
                    Text("Завершено місій: " + completed + " із " + missions.size, style = MaterialTheme.typography.labelMedium)
                    LinearProgressIndicator(progress = { if (missions.isEmpty()) 1f else completed.toFloat() / missions.size }, modifier = Modifier.fillMaxWidth())
                    if (currentMission != null) {
                        Text("Наступна місія: " + currentMission.key, fontWeight = FontWeight.SemiBold)
                        Text("Виконано вправ: " + currentExercise + " із " + currentMission.value.size, style = MaterialTheme.typography.bodySmall)
                        Button(onClick = onStart, modifier = Modifier.fillMaxWidth()) {
                            Text(if (currentExercise > 0) "Продовжити місію" else "Розпочати місію")
                        }
                    } else Text("Усі доступні місії глави завершено. Чудова робота!", fontWeight = FontWeight.SemiBold)
''')
replace(m, '''private fun ExerciseScreen(
    exercise: Exercise,
    onBack: () -> Unit,
    onResult: (Boolean) -> Unit
) {''', '''private fun ExerciseScreen(
    exercise: Exercise,
    onBack: () -> Unit,
    onContinue: () -> Unit,
    onResult: (Boolean) -> Unit
) {''')
replace(m, 'Button(onClick = onBack, modifier = Modifier.fillMaxWidth()) { Text("Продовжити") }', 'Button(onClick = onContinue, modifier = Modifier.fillMaxWidth()) { Text("Продовжити") }')

e = "app/src/main/java/ua/chroniclesofwords/data/ProgressEntity.kt"
replace(e, '    val completedMissions: Int = 0,', '    val completedMissions: Int = 0,\n    val currentExerciseIndex: Int = 0,')

d = "app/src/main/java/ua/chroniclesofwords/data/GameDatabase.kt"
replace(d, 'import androidx.room.RoomDatabase', 'import androidx.room.RoomDatabase\nimport androidx.room.migration.Migration\nimport androidx.sqlite.db.SupportSQLiteDatabase')
replace(d, '@Database(entities = [ProgressEntity::class], version = 1, exportSchema = false)', '@Database(entities = [ProgressEntity::class], version = 2, exportSchema = false)')
replace(d, '    companion object {', '''    companion object {
        private val MIGRATION_1_2 = object : Migration(1, 2) {
            override fun migrate(db: SupportSQLiteDatabase) {
                db.execSQL("ALTER TABLE player_progress ADD COLUMN currentExerciseIndex INTEGER NOT NULL DEFAULT 0")
            }
        }
''')
replace(d, '''                    "chronicles_of_words.db"
                ).build().also { INSTANCE = it }''', '''                    "chronicles_of_words.db"
                ).addMigrations(MIGRATION_1_2).build().also { INSTANCE = it }''')

# Split each rule into ordered difficulty missions instead of one topic-wide mission.
g = "app/src/main/java/ua/chroniclesofwords/learning/GameContent.kt"
replace(g, '''    val paragraph: String
)''', '''    val paragraph: String,
    val missionLevel: Int = 1
)''')
replace(g, '''    val exercises = listOf(''', '''    val exercises = listOf(''')
replace(g, '''    )
}''', '''    )

    // Mission identity is (rule, difficulty level), not the rule name alone.
    // Content can grow without merging later missions back into the first one.
    val missions: List<Map.Entry<String, List<Exercise>>>
        get() = exercises
            .groupBy { "${it.topic} · Місія ${it.missionLevel}" }
            .entries
            .toList()
}''')
replace(m, 'GameContent.exercises.groupBy { it.topic }.entries.toList()', 'GameContent.missions')

print("Mission progression patch applied.")
