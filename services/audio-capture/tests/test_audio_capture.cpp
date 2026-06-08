#include <gtest/gtest.h>
#include "audio_processor.h"
#include <vector>
#include <string>

// Test class that exposes protected methods or uses public API for testing
TEST(AudioProcessorTest, InitializationAndDefaults) {
    AudioProcessor processor;
    EXPECT_FALSE(processor.IsCapturing());
    EXPECT_FALSE(processor.IsAborted());
}

TEST(AudioProcessorTest, BlocklistSetAndGet) {
    AudioProcessor processor;
    processor.SetBlocklist({"NonExistentAppXYZ"});
    
    // NonExistentAppXYZ is not running, so it should return false
    EXPECT_FALSE(processor.IsBlocklistedAppRunning());
}

TEST(AudioProcessorTest, AbortLogicAndPurge) {
    AudioProcessor processor;
    
    // Trigger abort
    processor.AbortCapture("Test Whitelist Hit");
    
    EXPECT_TRUE(processor.IsAborted());
    EXPECT_FALSE(processor.IsCapturing());
}

int main(int argc, char **argv) {
    ::testing::InitGoogleTest(&argc, argv);
    return RUN_ALL_TESTS();
}
