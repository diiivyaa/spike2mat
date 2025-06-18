import os
from PySide6 import QtCore, QtGui, QtWidgets

CURRENT_DIR = os.path.dirname(os.path.realpath(__file__))

class CustomProgressBar(QtWidgets.QWidget):
    stepsChanged = QtCore.Signal(list)
    valueChanged = QtCore.Signal(int)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._labels = []
        self._value = 0

        self._animation = QtCore.QVariantAnimation(
            startValue=0.0, endValue=1.0, duration=500
        )
        self._animation.valueChanged.connect(self.update)

    def get_labels(self):
        return self._labels

    def set_labels(self, labels):
        self._labels = labels[:]
        self.stepsChanged.emit(self._labels)

    labels = QtCore.Property(
        list, fget=get_labels, fset=set_labels, notify=stepsChanged
    )

    def get_value(self):
        return self._value

    def set_value(self, value):
        if 0 <= value < len(self.labels) + 1:
            self._value = value
            self.valueChanged.emit(value)
            self.update()
            if self.value < len(self.labels):
                self._animation.start()

    value = QtCore.Property(int, fget=get_value, fset=set_value, notify=valueChanged)

    def sizeHint(self):
        return QtCore.QSize(320, 120)

    def paintEvent(self, event):

        grey = QtGui.QColor("#777")
        grey2 = QtGui.QColor("#dfe3e4")
        blue = QtGui.QColor("#3532d1")
        green = QtGui.QColor("#009900")
        white = QtGui.QColor("#fff")
        white.setAlpha(150)

        painter = QtGui.QPainter(self)

        painter.setRenderHints(QtGui.QPainter.Antialiasing)

        height = 5
        offset = 10

        painter.setBrush(white)
        painter.setPen(QtCore.Qt.NoPen)
        painter.drawRoundedRect(self.rect(), 20, 20)

        busy_rect = QtCore.QRect(0, 0, self.width(), height)
        busy_rect.adjust(offset, 0, -offset, 0)
        # busy_rect.moveCenter(self.rect().center())
        busy_rect.moveTop(15)

        painter.fillRect(busy_rect, grey2)

        number_of_steps = len(self.labels)

        if number_of_steps == 0:
            return

        step_width = busy_rect.width() / number_of_steps
        x = offset + step_width / 2
        y = busy_rect.center().y()
        radius = 10

        font_text = painter.font()

        font_icon = QtGui.QFont("Font Awesome 5 Free")
        font_icon.setPixelSize(radius)

        r = QtCore.QRect(0, 0, 1.5 * radius, 1.5 * radius)

        fm = QtGui.QFontMetrics(font_text)

        for i, text in enumerate(self.labels, 1):
            r.moveCenter(QtCore.QPoint(x, y))

            if i <= self.value:
                w = (
                    step_width
                    if i < self.value
                    else self._animation.currentValue() * step_width
                )
                r_busy = QtCore.QRect(0, 0, w, height)
                r_busy.moveCenter(busy_rect.center())

                if i < number_of_steps:
                    r_busy.moveLeft(x)
                    painter.fillRect(r_busy, blue)

                pen = QtGui.QPen(green)
                pen.setWidth(3)
                painter.setPen(pen)
                painter.setBrush(green)
                painter.drawEllipse(r)
                painter.setFont(font_icon)
                painter.setPen(white)
                painter.drawText(r, QtCore.Qt.AlignCenter, chr(0xF00C))
                painter.setPen(green)

            else:
                is_active = (self.value + 1) == i
                pen = QtGui.QPen(grey if is_active else grey2)
                pen.setWidth(3)
                painter.setPen(pen)
                painter.setBrush(white)
                painter.drawEllipse(r)
                painter.setPen(blue if is_active else QtGui.QColor("black"))

            rect = fm.boundingRect(text)
            rect.moveCenter(QtCore.QPoint(x, y + 2 * radius))
            painter.setFont(font_text)
            painter.drawText(rect, QtCore.Qt.AlignCenter, text)

            x += step_width
