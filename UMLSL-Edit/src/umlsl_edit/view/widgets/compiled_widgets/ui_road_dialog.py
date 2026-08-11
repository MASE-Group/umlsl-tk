# -*- coding: utf-8 -*-

################################################################################
## Form generated from reading UI file 'road_dialog.ui'
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
from PySide6.QtWidgets import (QAbstractSpinBox, QApplication, QComboBox, QDialog,
    QDoubleSpinBox, QGridLayout, QHBoxLayout, QLabel,
    QLayout, QLineEdit, QPushButton, QSizePolicy,
    QSpacerItem, QSpinBox, QVBoxLayout, QWidget)
from . import resources_rc

class Ui_Edit_Road_Dialog(object):
    def setupUi(self, Edit_Road_Dialog):
        if not Edit_Road_Dialog.objectName():
            Edit_Road_Dialog.setObjectName(u"Edit_Road_Dialog")
        Edit_Road_Dialog.resize(324, 291)
        sizePolicy = QSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Preferred)
        sizePolicy.setHorizontalStretch(0)
        sizePolicy.setVerticalStretch(0)
        sizePolicy.setHeightForWidth(Edit_Road_Dialog.sizePolicy().hasHeightForWidth())
        Edit_Road_Dialog.setSizePolicy(sizePolicy)
        Edit_Road_Dialog.setMinimumSize(QSize(0, 0))
        Edit_Road_Dialog.setMaximumSize(QSize(16777215, 16777215))
        Edit_Road_Dialog.setAutoFillBackground(False)
        Edit_Road_Dialog.setStyleSheet(u"QDialog {\n"
"    background-color: #011C26; \n"
"}\n"
"\n"
"QWidget {	\n"
"	font: 13pt \"Helvetica\";\n"
"    color: #F9F9F9;\n"
"}\n"
"\n"
"QLabel[class=label] {	\n"
"	font: 10pt;\n"
"    color: #F9F9F9;\n"
"}\n"
"\n"
"QWidget[class=container] {	\n"
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
"	\n"
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
"    selection-background-color: #011C26; \n"
"}\n"
"\n"
"/* --- The Dropdown Frame --- */\n"
"/* We target QListView specifically to override Mac defaults */\n"
"QComboBox QListView {\n"
"    background-color: #011C26;\n"
"    border: 1px solid #042"
                        "F40; /* Your custom border */\n"
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
"    padding-right: 15px; \n"
"}\n"
"\n"
"/* --- The Button Container Areas --- */\n"
"QSpinBox::up-button, QDoubleSpinBox::up-button {\n"
"    subcontrol-origin: border;\n"
"    subcontrol-position: top right"
                        ";\n"
"    width: 25px;\n"
"    \n"
"    border-left: 1px solid #042F40;\n"
"    border-top-right-radius: 6px;\n"
"    border-bottom: 1px solid #042F40;\n"
"    \n"
"    background-color: #011C26;\n"
"}\n"
"\n"
"QSpinBox::down-button, QDoubleSpinBox::down-button {\n"
"    subcontrol-origin: border;\n"
"    subcontrol-position: bottom right;\n"
"    width: 25px;\n"
"    \n"
"    border-left: 1px solid #042F40;\n"
"    border-bottom-right-radius: 6px;\n"
"    \n"
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
"/* (Assuming you are using the CSS Arrow hack from before. \n"
"   If using images, replace these with your image: url(...) code) */\n"
"\n"
"QSpinBox::up-arrow, QDoubleSpinBox::up-arrow {\n"
"    image: url(:/icons/icons/up.svg); /* You ne"
                        "ed to create this file */\n"
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
"    background-color: #032F40; \n"
"    border-radius: 16px;       \n"
"    border: none;\n"
"    text-align: center;\n"
"}\n"
"\n"
"QToolButton:hover {\n"
"    background-color: #314250; \n"
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
"QPushButton#b_save:hover {\n"
"    background-color: rgb(155, 191, 168); \n"
"}\n"
"QPushButton#b_save:pressed {\n"
"    background-color: #799582; \n"
"}\n"
"\n"
"QPushButton#b_delete {\n"
"	background-color: #042F40;\n"
"	color: #F9F9F9;\n"
"}\n"
"\n"
"QPushButton#b_delete:hover {\n"
"    background-color: #314250; \n"
""
                        "}\n"
"QPushButton#b_delete:pressed {\n"
"    background-color: #042F40; \n"
"}")
        self.verticalLayout_3 = QVBoxLayout(Edit_Road_Dialog)
        self.verticalLayout_3.setObjectName(u"verticalLayout_3")
        self.verticalLayout_3.setSizeConstraint(QLayout.SizeConstraint.SetFixedSize)
        self.widget = QWidget(Edit_Road_Dialog)
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
        self.gridLayout.setHorizontalSpacing(4)
        self.gridLayout.setVerticalSpacing(8)
        self.gridLayout.setContentsMargins(8, 4, 4, 4)
        self.label_5 = QLabel(self.widget1)
        self.label_5.setObjectName(u"label_5")
        self.label_5.setMinimumSize(QSize(75, 0))
        self.label_5.setAlignment(Qt.AlignmentFlag.AlignLeading|Qt.AlignmentFlag.AlignLeft|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout.addWidget(self.label_5, 0, 0, 1, 1)

        self.d_orientation = QComboBox(self.widget1)
        self.d_orientation.addItem("")
        self.d_orientation.addItem("")
        self.d_orientation.setObjectName(u"d_orientation")
        self.d_orientation.setMinimumSize(QSize(0, 24))
        self.d_orientation.setMaximumSize(QSize(16777215, 24))
        self.d_orientation.setFrame(False)

        self.gridLayout.addWidget(self.d_orientation, 1, 2, 1, 1)

        self.label_6 = QLabel(self.widget1)
        self.label_6.setObjectName(u"label_6")
        self.label_6.setMinimumSize(QSize(75, 0))

        self.gridLayout.addWidget(self.label_6, 1, 0, 1, 1)

        self.l_axis = QLabel(self.widget1)
        self.l_axis.setObjectName(u"l_axis")
        self.l_axis.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout.addWidget(self.l_axis, 3, 1, 1, 1)

        self.label_8 = QLabel(self.widget1)
        self.label_8.setObjectName(u"label_8")
        self.label_8.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.gridLayout.addWidget(self.label_8, 0, 1, 1, 1)

        self.label_7 = QLabel(self.widget1)
        self.label_7.setObjectName(u"label_7")
        self.label_7.setMinimumSize(QSize(75, 0))

        self.gridLayout.addWidget(self.label_7, 3, 0, 1, 1)

        self.t_name = QLineEdit(self.widget1)
        self.t_name.setObjectName(u"t_name")
        self.t_name.setMinimumSize(QSize(0, 24))
        self.t_name.setMaximumSize(QSize(16777215, 24))

        self.gridLayout.addWidget(self.t_name, 0, 2, 1, 1)

        self.s_position = QDoubleSpinBox(self.widget1)
        self.s_position.setObjectName(u"s_position")
        self.s_position.setMinimumSize(QSize(0, 24))
        self.s_position.setMaximumSize(QSize(16777215, 24))
        self.s_position.setMinimum(-500.000000000000000)
        self.s_position.setMaximum(500.000000000000000)
        self.s_position.setStepType(QAbstractSpinBox.StepType.DefaultStepType)

        self.gridLayout.addWidget(self.s_position, 3, 2, 1, 1)

        self.gridLayout.setColumnStretch(0, 1)
        self.gridLayout.setColumnStretch(1, 1)
        self.gridLayout.setColumnStretch(2, 4)

        self.General.addWidget(self.widget1)


        self.verticalLayout_3.addWidget(self.widget)

        self.widget2 = QWidget(Edit_Road_Dialog)
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

        self.label_4 = QLabel(self.widget3)
        self.label_4.setObjectName(u"label_4")
        font = QFont()
        font.setFamilies([u"Helvetica"])
        font.setPointSize(10)
        font.setBold(False)
        font.setItalic(False)
        self.label_4.setFont(font)
        self.label_4.setStyleSheet(u"color: #799582")
        self.label_4.setAlignment(Qt.AlignmentFlag.AlignRight|Qt.AlignmentFlag.AlignTrailing|Qt.AlignmentFlag.AlignVCenter)

        self.horizontalLayout_2.addWidget(self.label_4)

        self.horizontalSpacer = QSpacerItem(40, 0, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.horizontalLayout_2.addItem(self.horizontalSpacer)


        self.Lanes.addWidget(self.widget3)

        self.widget_2 = QWidget(self.widget2)
        self.widget_2.setObjectName(u"widget_2")
        self.widget_2.setMinimumSize(QSize(75, 0))
        self.gridLayout_2 = QGridLayout(self.widget_2)
        self.gridLayout_2.setObjectName(u"gridLayout_2")
        self.gridLayout_2.setHorizontalSpacing(4)
        self.gridLayout_2.setVerticalSpacing(8)
        self.gridLayout_2.setContentsMargins(8, 4, 4, 4)
        self.l_backward = QLabel(self.widget_2)
        self.l_backward.setObjectName(u"l_backward")
        self.l_backward.setMinimumSize(QSize(75, 0))

        self.gridLayout_2.addWidget(self.l_backward, 2, 0, 1, 1)

        self.s_forward = QSpinBox(self.widget_2)
        self.s_forward.setObjectName(u"s_forward")
        self.s_forward.setMinimumSize(QSize(32, 24))
        self.s_forward.setMaximumSize(QSize(16777215, 24))

        self.gridLayout_2.addWidget(self.s_forward, 0, 2, 1, 1)

        self.s_backward = QSpinBox(self.widget_2)
        self.s_backward.setObjectName(u"s_backward")
        self.s_backward.setMinimumSize(QSize(32, 24))
        self.s_backward.setMaximumSize(QSize(16777215, 24))

        self.gridLayout_2.addWidget(self.s_backward, 2, 2, 1, 1)

        self.l_forward = QLabel(self.widget_2)
        self.l_forward.setObjectName(u"l_forward")
        self.l_forward.setMinimumSize(QSize(75, 0))

        self.gridLayout_2.addWidget(self.l_forward, 0, 0, 1, 1)

        self.horizontalSpacer_2 = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)

        self.gridLayout_2.addItem(self.horizontalSpacer_2, 0, 1, 1, 1)

        self.gridLayout_2.setColumnStretch(0, 1)
        self.gridLayout_2.setColumnStretch(1, 1)
        self.gridLayout_2.setColumnStretch(2, 4)

        self.Lanes.addWidget(self.widget_2)


        self.verticalLayout_3.addWidget(self.widget2)

        self.verticalSpacer = QSpacerItem(20, 40, QSizePolicy.Policy.Minimum, QSizePolicy.Policy.Expanding)

        self.verticalLayout_3.addItem(self.verticalSpacer)

        self.Bottom = QHBoxLayout()
        self.Bottom.setObjectName(u"Bottom")
        self.Bottom.setContentsMargins(-1, 8, -1, -1)
        self.b_save = QPushButton(Edit_Road_Dialog)
        self.b_save.setObjectName(u"b_save")
        self.b_save.setMinimumSize(QSize(32, 32))
        self.b_save.setMaximumSize(QSize(16777215, 32))
        icon = QIcon()
        icon.addFile(u":/icons/icons/done_dark.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.b_save.setIcon(icon)

        self.Bottom.addWidget(self.b_save)

        self.b_delete = QPushButton(Edit_Road_Dialog)
        self.b_delete.setObjectName(u"b_delete")
        self.b_delete.setMinimumSize(QSize(32, 32))
        self.b_delete.setMaximumSize(QSize(16777215, 32))
        icon1 = QIcon()
        icon1.addFile(u":/icons/icons/delete.svg", QSize(), QIcon.Mode.Normal, QIcon.State.Off)
        self.b_delete.setIcon(icon1)

        self.Bottom.addWidget(self.b_delete)


        self.verticalLayout_3.addLayout(self.Bottom)


        self.retranslateUi(Edit_Road_Dialog)

        self.b_save.setDefault(True)


        QMetaObject.connectSlotsByName(Edit_Road_Dialog)
    # setupUi

    def retranslateUi(self, Edit_Road_Dialog):
        Edit_Road_Dialog.setWindowTitle(QCoreApplication.translate("Edit_Road_Dialog", u"Edit Road", None))
        self.label_2.setText(QCoreApplication.translate("Edit_Road_Dialog", u"General", None))
        self.label_2.setProperty(u"class", QCoreApplication.translate("Edit_Road_Dialog", u"label", None))
        self.widget1.setProperty(u"class", QCoreApplication.translate("Edit_Road_Dialog", u"container", None))
        self.label_5.setText(QCoreApplication.translate("Edit_Road_Dialog", u"Name", None))
        self.d_orientation.setItemText(0, QCoreApplication.translate("Edit_Road_Dialog", u"horizontal", None))
        self.d_orientation.setItemText(1, QCoreApplication.translate("Edit_Road_Dialog", u"vertical", None))

        self.label_6.setText(QCoreApplication.translate("Edit_Road_Dialog", u"Orientation", None))
        self.l_axis.setText(QCoreApplication.translate("Edit_Road_Dialog", u"y-Axis", None))
        self.l_axis.setProperty(u"class", QCoreApplication.translate("Edit_Road_Dialog", u"hint", None))
        self.label_8.setText(QCoreApplication.translate("Edit_Road_Dialog", u"unique", None))
        self.label_8.setProperty(u"class", QCoreApplication.translate("Edit_Road_Dialog", u"hint", None))
        self.label_7.setText(QCoreApplication.translate("Edit_Road_Dialog", u"Position", None))
        self.label_3.setText(QCoreApplication.translate("Edit_Road_Dialog", u"Lanes", None))
        self.label_3.setProperty(u"class", QCoreApplication.translate("Edit_Road_Dialog", u"label", None))
        self.label_4.setText(QCoreApplication.translate("Edit_Road_Dialog", u">= 1", None))
        self.label_4.setProperty(u"class", QCoreApplication.translate("Edit_Road_Dialog", u"label", None))
        self.widget_2.setProperty(u"class", QCoreApplication.translate("Edit_Road_Dialog", u"container", None))
        self.l_backward.setText(QCoreApplication.translate("Edit_Road_Dialog", u"Left", None))
        self.l_forward.setText(QCoreApplication.translate("Edit_Road_Dialog", u"Right", None))
        self.b_save.setText(QCoreApplication.translate("Edit_Road_Dialog", u"Save", None))
        self.b_delete.setText(QCoreApplication.translate("Edit_Road_Dialog", u"Delete", None))
    # retranslateUi

