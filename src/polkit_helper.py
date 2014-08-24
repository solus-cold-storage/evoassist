import dbus
import os

# Stolen from solusconfig

class PolkitHelper:

	def check_authorization(self, pid, action_id):

		# PolicyKit lives on the system bus
		bus = dbus.SystemBus()
		proxy = bus.get_object('org.freedesktop.PolicyKit1', '/org/freedesktop/PolicyKit1/Authority')

		# Create an automated interface object from org.freedesktop.PolicyKit1.Authority
		# Why? Because 1) You need this object and 2) Constantly getting dbus methods is a pain
		# in the hole. This automagics it a bit
		pk_authority = dbus.Interface(proxy,  dbus_interface='org.freedesktop.PolicyKit1.Authority')

		# We're enquiring about this process
		subject = ('unix-process',{'pid':dbus.UInt32(pid,variant_level=1),'start-time':dbus.UInt64(0,variant_level=1)})

		# No cancellation.
		CANCEL_ID = ''

		# AllowUserInteractionFlag
		flags = dbus.UInt32(1) 

		# Only for trusted senders, rarely used.
		details = {}

		# Returns all 3 of these. Fancy that. Invariably you'll only care whether the person is actually authorized or not.
		# i.e. you correctly created your dbus service so that the right group/user/etc can talk to it, and you created
		# your policykit configuration correctly
		(pk_granted,pk_other,pk_details) = pk_authority.CheckAuthorization(
			subject,
			action_id ,
			details,
			flags,
			CANCEL_ID,
			timeout=600) # Makes sense to use a timeout, you don't want your service to lockup

		return pk_granted
