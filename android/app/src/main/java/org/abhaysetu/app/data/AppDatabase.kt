package org.abhaysetu.app.data

import android.content.Context
import androidx.room.Database
import androidx.room.Entity
import androidx.room.PrimaryKey
import androidx.room.Room
import androidx.room.RoomDatabase
import androidx.room.Dao
import androidx.room.Insert
import androidx.room.OnConflictStrategy
import androidx.room.Query

@Entity(tableName = "sos_alerts")
data class SosEntity(
    @PrimaryKey val sosId: String,
    val payloadJson: String,
    val signature: String,
    val status: String,
    val honestMessage: String,
    val createdAt: Long,
    val attempts: Int = 0,
    val priority: String = "HIGH"
)

@Entity(tableName = "relay_seen")
data class RelaySeenEntity(
    @PrimaryKey val sosId: String,
    val seenAt: Long
)

@Dao
interface SosDao {
    @Insert(onConflict = OnConflictStrategy.REPLACE)
    suspend fun upsert(item: SosEntity)

    @Query("SELECT * FROM sos_alerts ORDER BY createdAt DESC")
    suspend fun all(): List<SosEntity>

    @Query("SELECT * FROM sos_alerts WHERE status != 'DELIVERED'")
    suspend fun pending(): List<SosEntity>

    @Insert(onConflict = OnConflictStrategy.IGNORE)
    suspend fun markSeen(item: RelaySeenEntity): Long

    @Query("SELECT sosId FROM relay_seen")
    suspend fun seenIds(): List<String>
}

@Database(entities = [SosEntity::class, RelaySeenEntity::class], version = 1)
abstract class AppDatabase : RoomDatabase() {
    abstract fun sosDao(): SosDao

    companion object {
        fun build(context: Context): AppDatabase =
            Room.databaseBuilder(context, AppDatabase::class.java, "abhaysetu.db").build()
    }
}
