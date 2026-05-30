#!/bin/bash
set -e

echo "Initializing Android Native Port Environment..."

# 1. Create Android project directories
mkdir -p app/src/main/cpp
mkdir -p app/src/main/java/com/pret/pokepinball
mkdir -p app/src/main/res/values
mkdir -p app/src/main/res/mipmap

# 2. Emit settings.gradle
cat << 'EOF' > settings.gradle
pluginManagement {
    repositories {
        google()
        mavenCentral()
        gradlePluginPortal()
    }
}
dependencyResolutionManagement {
    repositoriesMode.set(RepositoriesMode.FAIL_ON_PROJECT_REPOS)
    repositories {
        google()
        mavenCentral()
    }
}
rootProject.name = "PokePinball"
include ':app'
EOF

# 3. Emit Root build.gradle
cat << 'EOF' > build.gradle
plugins {
    id 'com.android.application' version '8.2.0' apply false
}
EOF

# 4. Emit App build.gradle (Configured for C++17 and CMake)
cat << 'EOF' > app/build.gradle
plugins {
    id 'com.android.application'
}

android {
    namespace 'com.pret.pokepinball'
    compileSdk 34

    defaultConfig {
        applicationId "com.pret.pokepinball"
        minSdk 26
        targetSdk 34
        versionCode 1
        versionName "1.0"

        externalNativeBuild {
            cmake {
                cppFlags "-std=c++17"
            }
        }
    }

    buildTypes {
        release {
            minifyEnabled false
            proguardFiles getDefaultProguardFile('proguard-android-optimize.txt'), 'proguard-rules.pro'
        }
    }

    externalNativeBuild {
        cmake {
            path "src/main/cpp/CMakeLists.txt"
            version "3.22.1"
        }
    }
}
EOF

# 5. Emit CMakeLists.txt (Base bridge for the Native Port)
cat << 'EOF' > app/src/main/cpp/CMakeLists.txt
cmake_minimum_required(VERSION 3.22.1)
project("pokepinball")

# The JNI bridge library
add_library(${CMAKE_PROJECT_NAME} SHARED engine_bridge.cpp)

find_library(log-lib log)
target_link_libraries(${CMAKE_PROJECT_NAME} ${log-lib})
EOF

# 6. Emit a dummy C++ file to prevent CMake failure during initial sync
cat << 'EOF' > app/src/main/cpp/engine_bridge.cpp
#include <jni.h>
#include <string>

extern "C" JNIEXPORT jstring JNICALL
Java_com_pret_pokepinball_MainActivity_stringFromJNI(
        JNIEnv* env,
        jobject /* this */) {
    std::string hello = "Native Engine Initialized";
    return env->NewStringUTF(hello.c_str());
}
EOF

# 7. Emit AndroidManifest.xml
cat << 'EOF' > app/src/main/AndroidManifest.xml
<?xml version="1.0" encoding="utf-8"?>
<manifest xmlns:android="http://schemas.android.com/apk/res/android">
    <application
        android:allowBackup="true"
        android:label="PokePinball"
        android:supportsRtl="true"
        android:theme="@android:style/Theme.NoTitleBar.Fullscreen">
        <activity
            android:name=".MainActivity"
            android:exported="true">
            <intent-filter>
                <action android:name="android.intent.action.MAIN" />
                <category android:name="android.intent.category.LAUNCHER" />
            </intent-filter>
        </activity>
    </application>
</manifest>
EOF

# 8. Emit a basic MainActivity.java so assembleDebug compiles successfully
cat << 'EOF' > app/src/main/java/com/pret/pokepinball/MainActivity.java
package com.pret.pokepinball;

import android.app.Activity;
import android.os.Bundle;
import android.widget.TextView;

public class MainActivity extends Activity {

    static {
        System.loadLibrary("pokepinball");
    }

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        
        TextView tv = new TextView(this);
        tv.setText(stringFromJNI());
        setContentView(tv);
    }

    public native String stringFromJNI();
}
EOF

# 9. Generate the Gradle Wrapper
# Now that a valid settings.gradle exists, Gradle will successfully initialize the wrapper.
echo "Project structure verified. Generating Gradle wrapper..."
if command -v gradle &> /dev/null; then
    gradle wrapper --gradle-version 8.4
else
    echo "ERROR: Local gradle installation not found in the path. Please ensure Gradle is installed in the Actions environment."
    exit 1
fi

if [ -f "gradlew" ]; then
    chmod +x gradlew
    echo "Gradle wrapper configured successfully."
fi

echo "Environment initialization complete."
