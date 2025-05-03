// App build.gradle.kts (place this in the app directory)

plugins {
    id("com.android.application")
    id("kotlin-android")
    id("dev.flutter.flutter-gradle-plugin")
}

android {
    namespace = "com.example.space_time"
    compileSdk = 34
    ndkVersion = "26.3.11579264"

    compileOptions {
        sourceCompatibility = JavaVersion.VERSION_11
        targetCompatibility = JavaVersion.VERSION_11
    }

    kotlinOptions {
        jvmTarget = JavaVersion.VERSION_11.toString()
    }

    defaultConfig {
        applicationId = "com.example.space_time"
        minSdk = 21
        targetSdk = 34
        versionCode = 1
        versionName = "1.0.0"
    }

    signingConfigs {
        create("release") {
            val keyPropsFile = file("../key.properties")
            if (keyPropsFile.exists()) {
                val keyProps = Properties()
                keyProps.load(FileInputStream(keyPropsFile))
                storeFile = file(keyProps.getProperty("storeFile"))
                storePassword = keyProps.getProperty("storePassword")
                keyAlias = keyProps.getProperty("keyAlias")
                keyPassword = keyProps.getProperty("keyPassword")
            } else {
                storeFile = file("C:/Users/rrai3/lol/android/app/LOL.jks")
                storePassword = "fuckinguglybitch"
                keyAlias = "lol"
                keyPassword = "fuckinguglybitch"
            }
        }
    }

    buildTypes {
        release {
            signingConfig = signingConfigs.getByName("release")
        }
    }
}

flutter {
    source = "../.."
}

// Add these imports at the top
import java.io.FileInputStream
import java.util.Properties