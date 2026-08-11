# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'settings_dialog.ui'
##
## Created by: Qt User Interface Compiler version 6.10.1
##
## WARNING! All changes made in this file will be lost when recompiling UI file!
################################################################################

from PySide6.QtCore import (QCoreApplication, QDate, QDateTime, QLocale,
    QMetaObject, QObject, QPoint, QRect,
    QSize, QTime, QUrl, Qt)
from PySide6.QtGui import (QBrush, QColor, QConicalGradient, QCursor,
    QFont, QFontDatabase, QGradient, QIcon,
    QImage, QKeySequence, QLinearGradient, QPainter,
    QPalette, QPixmap, QRadialGradient, QTransform)
from PySide6.QtWidgets import (QApplication, QCheckBox, QDialog, QDoubleSpinBox,
    QGridLayout, QHBoxLayout, QLabel, QLayout,
    QSizePolicy, QSpacerItem, QVBoxLayout, QWidget)
from . import resources_rc

class Ui_Settings_Dialog(object):
    def setupUi(self, Settings_Dialog):
        if not Settings_Dialog.objectName():
            Settings_Dialog.setObjectName(u"Settings_Dialog")
        Settings_Dialog.resize(324, 233)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(Settings_Dialog.sizePolicy().hasHeightForWidth())
        Settings_Dialog.setSizePolicy(sizePolicy)
        Settings_Dialog.setMinimumSize(QSize(0, 0))
        Settings_Dialog.setMaximumSize(QSize(999999, 9999))
        Settings_Dialog.setAutoFillBackground(False)
        Settings_Dialog.setStyleSheet(u"QDialog {\n"
"    background-color: #011C26;\n"
"}\n"
"\n"
"QWidget {\n"
"	font: 13pt \"Helvetica\";\n"
"    color: #F9F9F9;\n"
"}\n"
"\n"
"QLabel[class=label] {\n"
"	font: 10pt;\n"
"    color: #F9F9F9;\n"
"}\n"
"\n"
"QWidget[class=container] {\n"
"    background: #042F40;\n"
"	border-radius: 10px\n"
"}\n"
"\n"
"QLabel[class=hint] {\n"
"	color: #799582;\n"
"}\n"
"\n"
"QLabel[class=title] {\n"
"	font: 700 24pt;\n"
"}\n"
"\n"
"QLineEdit{\n"
"	background-color: #011C26;\n"
"	border: none;\n"
"	border-radius: 6px;\n"
"\n"
"}\n"
"\n"
"/* --- Main Box --- */\n"
"QComboBox {\n"
"    background-color: #011C26;\n"
"    border: none;\n"
"    border-radius: 6px;\n"
"    padding: 5px 10px;\n"
"    color: #F9F9F9;\n"
"    /* This helps selection color in some styles */\n"
"    selection-background-color: #011C26;\n"
"}\n"
"\n"
"/* --- The Dropdown Frame --- */\n"
"/* We target QListView specifically to override Mac defaults */\n"
"QComboBox QListView {\n"
"    background-color: #011C26;\n"
"    border: 1px solid #042F40; /"
                        "* Your custom border */\n"
"    outline: 0px; /* Removes the dotted/blue focus line */\n"
"    padding: 0px;\n"
"}\n"
"\n"
"\n"
"\n"
"/* --- The Arrow Button Area --- */\n"
"QComboBox::drop-down {\n"
"    subcontrol-origin: padding;\n"
"    subcontrol-position: top right;\n"
"    width: 24px;\n"
"    border-left: 1px solid #042F40; /* Optional: adds a separator */\n"
"    border-top-right-radius: 6px;\n"
"    border-bottom-right-radius: 6px;\n"
"}\n"
"\n"
"QComboBox::down-arrow {\n"
"    image: url(:/icons/icons/down.svg);\n"
"    width: 10px;\n"
"    height: 10px;\n"
"}\n"
"\n"
"/* --- Main Spinbox Styling (Applies to both) --- */\n"
"QSpinBox, QDoubleSpinBox {\n"
"    background-color: #011C26;\n"
"    border: none;\n"
"    border-radius: 6px;\n"
"    color: #F9F9F9;\n"
"    padding: 5px 10px;\n"
"    padding-right: 15px;\n"
"}\n"
"\n"
"/* --- The Button Container Areas --- */\n"
"QSpinBox::up-button, QDoubleSpinBox::up-button {\n"
"    subcontrol-origin: border;\n"
"    subcontrol-position: top right;\n"
" "
                        "   width: 25px;\n"
"\n"
"    border-left: 1px solid #042F40;\n"
"    border-top-right-radius: 6px;\n"
"    border-bottom: 1px solid #042F40;\n"
"\n"
"    background-color: #011C26;\n"
"}\n"
"\n"
"QSpinBox::down-button, QDoubleSpinBox::down-button {\n"
"    subcontrol-origin: border;\n"
"    subcontrol-position: bottom right;\n"
"    width: 25px;\n"
"\n"
"    border-left: 1px solid #042F40;\n"
"    border-bottom-right-radius: 6px;\n"
"\n"
"    background-color: #011C26;\n"
"}\n"
"\n"
"/* --- Hover Effects --- */\n"
"QSpinBox::up-button:hover, QDoubleSpinBox::up-button:hover,\n"
"QSpinBox::down-button:hover, QDoubleSpinBox::down-button:hover, QComboBox::drop-down:hover {\n"
"    background-color: #042F40;\n"
"}\n"
"\n"
"/* --- The Arrow Icons --- */\n"
"/* (Assuming you are using the CSS Arrow hack from before.\n"
"   If using images, replace these with your image: url(...) code) */\n"
"\n"
"QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {\n"
"    image: url(:/icons/icons/up.svg); /* You need to create this file *"
                        "/\n"
"    width: 10px;\n"
"    height: 10px;\n"
"}\n"
"\n"
"QSpinBox::down-arrow, QDoubleSpinBox::down-arrow {\n"
"    image: url(:/icons/icons/down.svg); /* You need to create this file */\n"
"    width: 10px;\n"
"    height: 10px;\n"
"}\n"
"\n"
"QToolButton {\n"
"    background-color: #032F40;\n"
"    border-radius: 16px;\n"
"    border: none;\n"
"    text-align: center;\n"
"}\n"
"\n"
"QToolButton:hover {\n"
"    background-color: #314250;\n"
"}\n"
"\n"
"QToolButton:pressed {\n"
"    background-color: #032F40;\n"
"}\n"
"\n"
"QPushButton {\n"
"	color: #011C26;\n"
"	border-radius: 16px\n"
"}\n"
"\n"
"QPushButton#b_save {\n"
"	background-color: #799582\n"
"}\n"
"\n"
"QPushButton#b_delete {\n"
"	background-color: #D97855\n"
"}\n"
"\n"
"/* 1. Base setup for the checkbox text and spacing */\n"
"QCheckBox {\n"
"    spacing: 12px;\n"
"    color: #ffffff; /* Text color */\n"
"}\n"
"\n"
"/* 2. Define the size and shape of the box (The Indicator) */\n"
"QCheckBox::indicator {\n"
"    width: 16px;\n"
"    height: 16px;\n"
""
                        "    border-radius: 6px;  /* This creates the \"squircle\" roundness */\n"
"    border: 2px solid #9ab5a3; /* The Sage Green border */\n"
"}\n"
"\n"
"/* 3. The Unchecked State (Empty with outline) */\n"
"QCheckBox::indicator:unchecked {\n"
"    background-color: transparent;\n"
"}\n"
"\n"
"/* Optional: Slight hover effect for unchecked */\n"
"QCheckBox::indicator:unchecked:hover {\n"
"    background-color: rgba(154, 181, 163, 0.2);\n"
"}\n"
"\n"
"/* 4. The Checked State (Filled Green) */\n"
"QCheckBox::indicator:checked {\n"
"    background-color: #9ab5a3;\n"
"    border: 2px solid #9ab5a3;\n"
"\n"
"    /* CRITICAL: You must replace this path with your own icon!\n"
"       Since we painted over the native box, we have to put the checkmark back manually. */\n"
"    image: url(:/icons/icons/checkmark.svg);\n"
"}")
        self.verticalLayout_3 = QVBoxLayout(Settings_Dialog)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        self.widget = QWidget(Settings_Dialog)
        self.widget.setObjectName(u"widget")
        self.General = QVBoxLayout(self.widget)
        self.General.setSpacing(0)
        self.General.setObjectName(u"General")
        self.General.setSizeConstraint(QLayout.SizeConstraint.SetDefaultConstraint)
        self.General.setContentsMargins(0, 8, 0, 0)
        self.widget_3 = QWidget(self.widget)
        self.widget_3.setObjectName(u"widget_3")
        self.horizontalLayout = QHBoxLayout(self.widget_3)
        self.horizontalLayout.setObjectName(u"horizontalLayout")
        self.horizontalLayout.setContentsMargins(8, 0, 0, 4)
        self.label_2 = QLabel(self.widget_3)
        self.label_2.setObjectName(u"label_2")
        self.label_2.setMargin(0)

        self.horizontalLayout.addWidget(self.label_2)


        self.General.addWidget(self.widget_3, 0, Qt.AlignmentFlag.AlignLeft)

        self.widget1 = QWidget(self.widget)
        self.widget1.setObjectName(u"widget1")
        self.widget1.setMinimumSize(QSize(300, 0))
        self.widget1.setMaximumSize(QSize(300, 16777215))
        self.gridLayout = QGridLayout(self.widget1)
        self.gridLayout.setObjectName(u"gridLayout")
        self.gridLayout.setVerticalSpacing(16)
        self.label_9 = QLabel(self.widget1)
        self.label_9.setObjectName(u"label_9")
        self.label_9.setMinimumSize(QSize(75, 0))

        self.gridLayout.addWidget(self.label_9, 0, 0, 1, 1)

        self.c_coordinate_system = QCheckBox(self.widget1)
        self.c_coordinate_system.setObjectName(u"c_coordinate_system")
        self.c_coordinate_system.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.c_coordinate_system.setText(u"")
        self.c_coordinate_system.setChecked(True)
        self.c_coordinate_system.setAutoRepeat(False)
        self.c_coordinate_system.setTristate(False)

        self.gridLayout.addWidget(self.c_coordinate_system, 0, 1, 1, 2)

        self.label_6 = QLabel(self.widget1)
        self.label_6.setObjectName(u"label_6")
        self.label_6.setMinimumSize(QSize(75, 0))

        self.gridLayout.addWidget(self.label_6, 1, 0, 1, 1)

        self.c_grid = QCheckBox(self.widget1)
        self.c_grid.setObjectName(u"c_grid")
        self.c_grid.setLayoutDirection(Qt.LayoutDirection.RightToLeft)
        self.c_grid.setText(u"")
        self.c_grid.setChecked(True)
        self.c_grid.setAutoRepeat(False)
        self.c_grid.setTristate(False)

        self.gridLayout.addWidget(self.c_grid, 1, 1, 1, 2)

        self.l_reserved = QLabel(self.widget1)
        self.l_reserved.setObjectName(u"l_reserved")
        self.l_reserved.setMinimumSize(QSize(75, 0))
        self.l_reserved.setAlignment(Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout.addWidget(self.l_reserved, 2, 0, 1, 1)

        self.s_reserved = QSpacerItem(40, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout.addItem(self.s_reserved, 2, 1, 1, 1)

        self.c_savty_space = QCheckBox(self.widget1)
        self.c_savty_space.setObjectName(u"c_savty_space")
        self.c_savty_space.setLayoutDirection(Qt.LayoutDirection.RightToLeft)

        self.gridLayout.addWidget(self.c_savty_space, 2, 2, 1, 1)


        self.General.addWidget(self.widget1)


        self.verticalLayout_3.addWidget(self.widget)

        self.widget2 = QWidget(Settings_Dialog)
        self.widget2.setObjectName(u"widget2")
        self.Lanes = QVBoxLayout(self.widget2)
        self.Lanes.setSpacing(0)
        self.Lanes.setObjectName(u"Lanes")
        self.Lanes.setSizeConstraint(QLayout.SizeConstraint.SetDefaultConstraint)
        self.Lanes.setContentsMargins(0, 0, 0, 0)
        self.widget3 = QWidget(self.widget2)
        self.widget3.setObjectName(u"widget3")
        sizePolicy1 = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Minimum)
        sizePolicy1.setHorizontalStretch(0)
        sizePolicy1.setVerticalStretch(0)
        sizePolicy1.setHeightForWidth(self.widget3.sizePolicy().hasHeightForWidth())
        self.widget3.setSizePolicy(sizePolicy1)
        self.horizontalLayout_2 = QHBoxLayout(self.widget3)
        self.horizontalLayout_2.setSpacing(8)
        self.horizontalLayout_2.setObjectName(u"horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(8, 0, 4, 4)
        self.label_3 = QLabel(self.widget3)
        self.label_3.setObjectName(u"label_3")
        sizePolicy2 = QSizePolicy(QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Preferred)
        sizePolicy2.setHorizontalStretch(0)
        sizePolicy2.setVerticalStretch(0)
        sizePolicy2.setHeightForWidth(self.label_3.sizePolicy().hasHeightForWidth())
        self.label_3.setSizePolicy(sizePolicy2)

        self.horizontalLayout_2.addWidget(self.label_3)


        self.Lanes.addWidget(self.widget3)

        self.widget_2 = QWidget(self.widget2)
        self.widget_2.setObjectName(u"widget_2")
        self.widget_2.setMinimumSize(QSize(75, 0))
        self.gridLayout_2 = QGridLayout(self.widget_2)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setHorizontalSpacing(4)
        self.gridLayout_2.setVerticalSpacing(8)
        self.gridLayout_2.setContentsMargins(8, 4, 4, 4)
        self.s_braking = QDoubleSpinBox(self.widget_2)
        self.s_braking.setObjectName(u"s_braking")
        self.s_braking.setMaximum(10000.000000000000000)

        self.gridLayout_2.addWidget(self.s_braking, 1, 2, 1, 1)

        self.label_11 = QLabel(self.widget_2)
        self.label_11.setObjectName(u"label_11")
        self.label_11.setMinimumSize(QSize(75, 0))

        self.gridLayout_2.addWidget(self.label_11, 1, 0, 1, 1)

        self.label_4 = QLabel(self.widget_2)
        self.label_4.setObjectName(u"label_4")
        self.label_4.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout_2.addWidget(self.label_4, 1, 1, 1, 1)

        self.label_7 = QLabel(self.widget_2)
        self.label_7.setObjectName(u"label_7")

        self.gridLayout_2.addWidget(self.label_7, 2, 0, 1, 1)

        self.label_8 = QLabel(self.widget_2)
        self.label_8.setObjectName(u"label_8")

        self.gridLayout_2.addWidget(self.label_8, 2, 1, 1, 1)

        self.s_accerleration = QDoubleSpinBox(self.widget_2)
        self.s_accerleration.setObjectName(u"s_accerleration")
        self.s_accerleration.setMaximum(10000.000000000000000)

        self.gridLayout_2.addWidget(self.s_accerleration, 2, 2, 1, 1)

        self.gridLayout_2.setColumnStretch(0, 4)
        self.gridLayout_2.setColumnStretch(1, 1)
        self.gridLayout_2.setColumnStretch(2, 3)

        self.Lanes.addWidget(self.widget_2)


        self.verticalLayout_3.addWidget(self.widget2)


        self.retranslateUi(Settings_Dialog)

        QMetaObject.connectSlotsByName(Settings_Dialog)
    # setupUi

    def retranslateUi(self, Settings_Dialog):
        Settings_Dialog.setWindowTitle(QCoreApplication.translate("Settings_Dialog", u"Settings", None))
        self.label_2.setText(QCoreApplication.translate("Settings_Dialog", u"Rendering", None))
        self.label_2.setProperty(u"class", QCoreApplication.translate("Settings_Dialog", u"label", None))
        self.widget1.setProperty(u"class", QCoreApplication.translate("Settings_Dialog", u"container", None))
        self.label_9.setText(QCoreApplication.translate("Settings_Dialog", u"Show coordinate system", None))
        self.label_6.setText(QCoreApplication.translate("Settings_Dialog", u"Show background grid", None))
        self.l_reserved.setText(QCoreApplication.translate("Settings_Dialog", u"Show reserved space", None))
        self.c_savty_space.setText("")
        self.label_3.setText(QCoreApplication.translate("Settings_Dialog", u"Simulation", None))
        self.label_3.setProperty(u"class", QCoreApplication.translate("Settings_Dialog", u"label", None))
        self.widget_2.setProperty(u"class", QCoreApplication.translate("Settings_Dialog", u"container", None))
        self.label_11.setText(QCoreApplication.translate("Settings_Dialog", u"Braking deceleration", None))
        self.label_4.setText(QCoreApplication.translate("Settings_Dialog", u"u/s^2", None))
        self.label_4.setProperty(u"class", QCoreApplication.translate("Settings_Dialog", u"hint", None))
        self.label_7.setText(QCoreApplication.translate("Settings_Dialog", u"Max velocity", None))
        self.label_8.setText(QCoreApplication.translate("Settings_Dialog", u"u/s", None))
        self.label_8.setProperty(u"class", QCoreApplication.translate("Settings_Dialog", u"hint", None))
    # retranslateUi

