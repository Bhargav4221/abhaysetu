package org.abhaysetu.app

import android.app.Application
import org.abhaysetu.app.data.AppDatabase

class AbhaySetuApp : Application() {
    val database by lazy { AppDatabase.build(this) }
}
