# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'main.ui'
##
## Created by: Qt User Interface Compiler version 6.10.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QAction, QBrush, QColor, QConicalGradient,
    QCursor, QFont, QFontDatabase, QGradient,
    QIcon, QImage, QKeySequence, QLinearGradient,
    QPainter, QPalette, QPixmap, QRadialGradient,
    QTransform)
from PySide6.QtQuickWidgets import QQuickWidget
from PySide6.QtWidgets import (QApplication, QFrame, QGraphicsView, QHBoxLayout,
    QLabel, QMainWindow, QMenu, QMenuBar,
    QScrollArea, QSizePolicy, QSplitter, QToolButton,
    QVBoxLayout, QWidget)
from . import resources_rc

class Ui_MainWindow(object):
    def setupUi(self, MainWindow):
        if not MainWindow.objectName():
            MainWindow.setObjectName(u"MainWindow")
        MainWindow.resize(1009, 873)
        MainWindow.setStyleSheet(u"QMainWindow {\n"
"    background-color: #011C26; \n"
"}\n"
"\n"
"QScrollArea {\n"
"    background-color: transparent;\n"
"    border: none;\n"
"}\n"
"\n"
"QListView {\n"
"	background-color: transparent;\n"
"    border: none;\n"
"}\n"
"\n"
"QWidget {	\n"
"	font: 13pt \"Helvetica\";\n"
"    color: #F9F9F9;\n"
"}\n"
"\n"
"QWidget#c {	\n"
"	background-color: transparent;\n"
"}\n"
"\n"
"QFrame#zoom_buttons {\n"
"	background-color: transparent;\n"
"	border: none;\n"
"}\n"
"\n"
"QLabel#list_titel,#list_titel_2, #list_titel_3 {\n"
"	font: 700 32pt;\n"
"	color: #F9F9F9;\n"
"	QToolButton {\n"
"		background-color: red\n"
"	}\n"
"}\n"
"\n"
"QToolButton {\n"
"    background-color: #032F40; \n"
"    border-radius: 16px;       \n"
"    border: none;\n"
"    text-align: center;\n"
"}\n"
"\n"
"QToolButton#b_sidebar_toggle {\n"
"    border-top-left-radius: 0px;\n"
"    border-top-right-radius: 16px;\n"
"    border-bottom-left-radius: 0px;\n"
"    border-bottom-right-radius: 16px;   \n"
"}\n"
"\n"
"QToolButton:hover {\n"
"    ba"
                        "ckground-color: #084D68; \n"
"}\n"
"\n"
"QToolButton:pressed {\n"
"    background-color: #032F40;\n"
"}\n"
"\n"
"QToolButton#b_minus, #b_plus, #b_sidebar_toggle {\n"
"    background-color: #011C26; \n"
"}\n"
"QToolButton#b_minus:hover, #b_plus:hover, #b_sidebar_toggle:hover {\n"
"    background-color: #084D68; \n"
"}\n"
"QToolButton#b_minus:pressed, #b_plus:pressed, #b_sidebar_toggle:pressed {\n"
"    background-color: #011C26; \n"
"}\n"
"\n"
"QSplitter::handle {\n"
"    background-color: #032F40;\n"
"}\n"
"\n"
"QSplitter::handle:vertical {\n"
"    height: 4px; \n"
"}\n"
"\n"
"QSplitter::handle:vertical:hover {\n"
"    background-color: #084D68; \n"
"}\n"
"\n"
"/* --- Menu Bar Styling --- */\n"
"QMenuBar {\n"
"    background-color: #011C26;\n"
"    color: #F9F9F9;\n"
"}\n"
"\n"
"QMenuBar::item {\n"
"    background-color: transparent;\n"
"}\n"
"\n"
"QMenuBar::item:selected {\n"
"    background-color: #084D68; /* Matches your button hover color */\n"
"}\n"
"\n"
"/* --- Dropdown Menu Styling --- */\n"
"QMenu {\n"
""
                        "    background-color: #032F40; /* Slightly lighter than main window to stand out */\n"
"    color: #F9F9F9;\n"
"    border: 1px solid #084D68; /* Optional: adds a border to define the menu */\n"
"}\n"
"\n"
"QMenu::item {\n"
"    padding: 5px 20px; /* Gives the items some breathing room */\n"
"}\n"
"\n"
"QMenu::item:selected {\n"
"    background-color: #084D68; /* Hover color for menu items */\n"
"}")
        MainWindow.setUnifiedTitleAndToolBarOnMac(False)
        self.actionSave = QAction(MainWindow)
        self.actionSave.setObjectName(u"actionSave")
        icon = QIcon()
        icon.addFile(u":/icons/icons/save.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.actionSave.setIcon(icon)
        self.actionSave_As = QAction(MainWindow)
        self.actionSave_As.setObjectName(u"actionSave_As")
        icon1 = QIcon()
        icon1.addFile(u":/icons/icons/save_as.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.actionSave_As.setIcon(icon1)
        self.actionOpen = QAction(MainWindow)
        self.actionOpen.setObjectName(u"actionOpen")
        icon2 = QIcon()
        icon2.addFile(u":/icons/icons/file_open.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.actionOpen.setIcon(icon2)
        self.actionSettings = QAction(MainWindow)
        self.actionSettings.setObjectName(u"actionSettings")
        icon3 = QIcon()
        icon3.addFile(u":/icons/icons/settings.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.actionSettings.setIcon(icon3)
        self.actionExport_to_UMLSL_Sim = QAction(MainWindow)
        self.actionExport_to_UMLSL_Sim.setObjectName(u"actionExport_to_UMLSL_Sim")
        self.actionImport_from_UMLSL_Sim = QAction(MainWindow)
        self.actionImport_from_UMLSL_Sim.setObjectName(u"actionImport_from_UMLSL_Sim")
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName(u"centralwidget")
        self.horizontalLayout = QHBoxLayout(self.centralwidget)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(0, 0, 0, 0)
        self.sidebar = QScrollArea(self.centralwidget)
        self.sidebar.setObjectName(u"sidebar")
        self.sidebar.setMinimumSize(QSize(300, 0))
        self.sidebar.setMaximumSize(QSize(300, 16777215))
        self.sidebar.setStyleSheet(u"")
        self.sidebar.setWidgetResizable(True)
        self.c = QWidget()
        self.c.setObjectName(u"c")
        self.c.setGeometry(QRect(0, 0, 300, 843))
        self.verticalLayout_5 = QVBoxLayout(self.c)
        self.verticalLayout_5.setObjectName(u"verticalLayout_5")
        self.splitter = QSplitter(self.c)
        self.splitter.setObjectName(u"splitter")
        self.splitter.setMidLineWidth(32)
        self.splitter.setOrientation(Qt.Orientation.Vertical)
        self.splitter.setChildrenCollapsible(False)
        self.layoutWidget = QWidget(self.splitter)
        self.layoutWidget.setObjectName(u"layoutWidget")
        self.verticalLayout = QVBoxLayout(self.layoutWidget)
        self.verticalLayout.setObjectName(u"verticalLayout")
        self.verticalLayout.setContentsMargins(0, 16, 0, 0)
        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(-1, -1, 8, -1)
        self.list_titel_3 = QLabel(self.layoutWidget)
        self.list_titel_3.setObjectName(u"list_titel_3")

        self.horizontalLayout_2.addWidget(self.list_titel_3)

        self.b_add_road = QToolButton(self.layoutWidget)
        self.b_add_road.setObjectName(u"b_add_road")
        self.b_add_road.setMinimumSize(QSize(32, 32))
        self.b_add_road.setMaximumSize(QSize(32, 32))
        icon4 = QIcon()
        icon4.addFile(u":/icons/icons/add.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.b_add_road.setIcon(icon4)
        self.b_add_road.setIconSize(QSize(20, 20))

        self.horizontalLayout_2.addWidget(self.b_add_road)


        self.verticalLayout.addLayout(self.horizontalLayout_2)

        self.q_roads = QQuickWidget(self.layoutWidget)
        self.q_roads.setObjectName(u"q_roads")
        self.q_roads.setResizeMode(QQuickWidget.ResizeMode.SizeRootObjectToView)

        self.verticalLayout.addWidget(self.q_roads)

        self.splitter.addWidget(self.layoutWidget)
        self.layoutWidget1 = QWidget(self.splitter)
        self.layoutWidget1.setObjectName(u"layoutWidget1")
        self.verticalLayout_3 = QVBoxLayout(self.layoutWidget1)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(0, 16, 0, 0)
        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName(u"horizontalLayout_3")
        self.horizontalLayout_3.setContentsMargins(-1, -1, 8, -1)
        self.list_titel_2 = QLabel(self.layoutWidget1)
        self.list_titel_2.setObjectName(u"list_titel_2")

        self.horizontalLayout_3.addWidget(self.list_titel_2)

        self.b_add_car = QToolButton(self.layoutWidget1)
        self.b_add_car.setObjectName(u"b_add_car")
        self.b_add_car.setMinimumSize(QSize(32, 32))
        self.b_add_car.setMaximumSize(QSize(32, 32))
        self.b_add_car.setIcon(icon4)
        self.b_add_car.setIconSize(QSize(20, 20))

        self.horizontalLayout_3.addWidget(self.b_add_car)


        self.verticalLayout_3.addLayout(self.horizontalLayout_3)

        self.q_cars = QQuickWidget(self.layoutWidget1)
        self.q_cars.setObjectName(u"q_cars")
        self.q_cars.setResizeMode(QQuickWidget.ResizeMode.SizeRootObjectToView)

        self.verticalLayout_3.addWidget(self.q_cars)

        self.splitter.addWidget(self.layoutWidget1)
        self.layoutWidget2 = QWidget(self.splitter)
        self.layoutWidget2.setObjectName(u"layoutWidget2")
        self.verticalLayout_4 = QVBoxLayout(self.layoutWidget2)
        self.verticalLayout_4.setObjectName(u"verticalLayout_4")
        self.verticalLayout_4.setContentsMargins(0, 16, 0, 0)
        self.horizontalLayout_4 = QHBoxLayout()
        self.horizontalLayout_4.setObjectName(u"horizontalLayout_4")
        self.horizontalLayout_4.setContentsMargins(-1, -1, 8, -1)
        self.list_titel = QLabel(self.layoutWidget2)
        self.list_titel.setObjectName(u"list_titel")

        self.horizontalLayout_4.addWidget(self.list_titel)

        self.b_add_query = QToolButton(self.layoutWidget2)
        self.b_add_query.setObjectName(u"b_add_query")
        self.b_add_query.setMinimumSize(QSize(32, 32))
        self.b_add_query.setMaximumSize(QSize(32, 32))
        self.b_add_query.setIcon(icon4)
        self.b_add_query.setIconSize(QSize(20, 20))

        self.horizontalLayout_4.addWidget(self.b_add_query)


        self.verticalLayout_4.addLayout(self.horizontalLayout_4)

        self.q_queries = QQuickWidget(self.layoutWidget2)
        self.q_queries.setObjectName(u"q_queries")
        self.q_queries.setResizeMode(QQuickWidget.ResizeMode.SizeRootObjectToView)

        self.verticalLayout_4.addWidget(self.q_queries)

        self.splitter.addWidget(self.layoutWidget2)

        self.verticalLayout_5.addWidget(self.splitter)

        self.sidebar.setWidget(self.c)

        self.horizontalLayout.addWidget(self.sidebar)

        self.graphicsView = QGraphicsView(self.centralwidget)
        self.graphicsView.setObjectName(u"graphicsView")

        self.horizontalLayout.addWidget(self.graphicsView)

        self.b_sidebar_toggle = QToolButton(self.centralwidget)
        self.b_sidebar_toggle.setObjectName(u"b_sidebar_toggle")
        self.b_sidebar_toggle.setMinimumSize(QSize(32, 32))
        self.b_sidebar_toggle.setMaximumSize(QSize(32, 32))
        icon5 = QIcon()
        icon5.addFile(u":/icons/icons/menu.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.b_sidebar_toggle.setIcon(icon5)

        self.horizontalLayout.addWidget(self.b_sidebar_toggle)

        self.zoom_buttons = QFrame(self.centralwidget)
        self.zoom_buttons.setObjectName(u"zoom_buttons")
        self.zoom_buttons.setMinimumSize(QSize(32, 0))
        self.zoom_buttons.setMaximumSize(QSize(32, 16777215))
        self.zoom_buttons.setStyleSheet(u"")
        self.zoom_buttons.setFrameShape(QFrame.Shape.StyledPanel)
        self.zoom_buttons.setFrameShadow(QFrame.Shadow.Raised)
        self.verticalLayout_2 = QVBoxLayout(self.zoom_buttons)
        self.verticalLayout_2.setObjectName(u"verticalLayout_2")
        self.verticalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.b_plus = QToolButton(self.zoom_buttons)
        self.b_plus.setObjectName(u"b_plus")
        self.b_plus.setMinimumSize(QSize(32, 32))
        self.b_plus.setMaximumSize(QSize(32, 32))
        self.b_plus.setIcon(icon4)

        self.verticalLayout_2.addWidget(self.b_plus)

        self.b_minus = QToolButton(self.zoom_buttons)
        self.b_minus.setObjectName(u"b_minus")
        self.b_minus.setMinimumSize(QSize(32, 32))
        self.b_minus.setMaximumSize(QSize(32, 32))
        icon6 = QIcon()
        icon6.addFile(u":/icons/icons/remove.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.b_minus.setIcon(icon6)

        self.verticalLayout_2.addWidget(self.b_minus)


        self.horizontalLayout.addWidget(self.zoom_buttons)

        MainWindow.setCentralWidget(self.centralwidget)
        self.menuBar = QMenuBar(MainWindow)
        self.menuBar.setObjectName(u"menuBar")
        self.menuBar.setGeometry(QRect(0, 0, 1009, 30))
        self.menuBar.setDefaultUp(False)
        self.menuBar.setNativeMenuBar(True)
        self.menuFile = QMenu(self.menuBar)
        self.menuFile.setObjectName(u"menuFile")
        self.menuSettings = QMenu(self.menuBar)
        self.menuSettings.setObjectName(u"menuSettings")
        MainWindow.setMenuBar(self.menuBar)

        self.menuBar.addAction(self.menuFile.menuAction())
        self.menuBar.addAction(self.menuSettings.menuAction())
        self.menuFile.addAction(self.actionSave)
        self.menuFile.addAction(self.actionSave_As)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.actionOpen)
        self.menuFile.addSeparator()
        self.menuFile.addAction(self.actionExport_to_UMLSL_Sim)
        self.menuFile.addAction(self.actionImport_from_UMLSL_Sim)
        self.menuSettings.addAction(self.actionSettings)

        self.retranslateUi(MainWindow)

        QMetaObject.connectSlotsByName(MainWindow)
    # setupUi

    def retranslateUi(self, MainWindow):
        MainWindow.setWindowTitle(QCoreApplication.translate("MainWindow", u"UMLSL-Edit", None))
        self.actionSave.setText(QCoreApplication.translate("MainWindow", u"Save", None))
        self.actionSave_As.setText(QCoreApplication.translate("MainWindow", u"Save As", None))
        self.actionOpen.setText(QCoreApplication.translate("MainWindow", u"Open", None))
        self.actionSettings.setText(QCoreApplication.translate("MainWindow", u"Open Settings", None))
        self.actionExport_to_UMLSL_Sim.setText(QCoreApplication.translate("MainWindow", u"Export to UMLSL-Sim", None))
        self.actionImport_from_UMLSL_Sim.setText(QCoreApplication.translate("MainWindow", u"Import from UMLSL-Sim", None))
        self.list_titel_3.setText(QCoreApplication.translate("MainWindow", u"Roads", None))
        self.b_add_road.setText("")
        self.list_titel_2.setText(QCoreApplication.translate("MainWindow", u"Cars", None))
        self.b_add_car.setText("")
        self.list_titel.setText(QCoreApplication.translate("MainWindow", u"Queries", None))
        self.b_add_query.setText("")
        self.b_sidebar_toggle.setText("")
        self.b_plus.setText("")
        self.b_minus.setText("")
        self.menuFile.setTitle(QCoreApplication.translate("MainWindow", u"File", None))
        self.menuSettings.setTitle(QCoreApplication.translate("MainWindow", u"Settings", None))
    # retranslateUi

