# raye-first-run: the welcome after the first sign-in (see main.cpp for
# what it replaces). The two QML files are built into the binary, so the
# package ships one file in /usr/bin and nothing else of its own; the look
# comes from the installed org.raye.setup at run time.
find_package(Qt6 6.8 REQUIRED COMPONENTS Gui Qml Quick)

qt_add_executable(raye-first-run main.cpp)
set_target_properties(raye-first-run PROPERTIES AUTOMOC ON)
target_link_libraries(raye-first-run PRIVATE Qt6::Gui Qt6::Qml Qt6::Quick)
# Every .qml and .js of qml/ goes in here, named. The page is also
# loaded straight from the source folder by tests/ui/tst_firstrun.qml, so
# a file left out of this list is found by every test and missing from
# the binary: debian/test_raye_paths.py compares the two.
qt_add_resources(raye-first-run "firstrun"
    PREFIX /raye/firstrun
    BASE qml
    FILES qml/Main.qml qml/RecoveryKeyPage.qml qml/words.js)
install(TARGETS raye-first-run RUNTIME DESTINATION ${CMAKE_INSTALL_BINDIR})
